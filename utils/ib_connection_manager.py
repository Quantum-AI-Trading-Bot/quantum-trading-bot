#!/usr/bin/env python3
"""
IB Connection Manager with Auto-Reconnect
Handles connection resilience, automatic reconnection, and health monitoring

Features:
- Exponential backoff retry logic
- Connection health monitoring with heartbeat
- Automatic reconnection on disconnect
- Circuit breaker pattern for repeated failures
- Event callbacks for connection state changes

Author: David Sanker
Date: January 28, 2026
"""

import time
import logging
import threading
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from ib_insync import IB, util

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Too many failures, stop trying
    HALF_OPEN = "half_open"  # Testing if connection recovers


class IBConnectionManager:
    """
    Manages IB connection with automatic reconnection and health monitoring
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 1,
        timeout: int = 15,
        max_retries: int = 10,
        initial_retry_delay: float = 2.0,
        max_retry_delay: float = 300.0,
        heartbeat_interval: int = 30,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        on_connected: Optional[Callable] = None,
        on_disconnected: Optional[Callable] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Initialize connection manager

        Args:
            host: IB Gateway host
            port: IB Gateway port
            client_id: Unique client ID
            timeout: Connection timeout in seconds
            max_retries: Maximum reconnection attempts (-1 for infinite)
            initial_retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
            heartbeat_interval: Seconds between heartbeat checks
            circuit_breaker_threshold: Failed attempts before opening circuit
            circuit_breaker_timeout: Seconds before trying again after circuit opens
            on_connected: Callback when connection established
            on_disconnected: Callback when disconnected
            on_error: Callback for errors
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.heartbeat_interval = heartbeat_interval
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Callbacks
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.on_error = on_error

        # State
        self.ib = IB()
        self.state = ConnectionState.DISCONNECTED
        self.circuit_state = CircuitBreakerState.CLOSED
        self.retry_count = 0
        self.current_retry_delay = initial_retry_delay
        self.consecutive_failures = 0
        self.last_heartbeat = None
        self.circuit_opened_at = None

        # Threading
        self.is_running = False
        self.reconnect_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_connections': 0,
            'total_disconnections': 0,
            'total_reconnections': 0,
            'total_failures': 0,
            'last_connected': None,
            'last_disconnected': None,
            'uptime_start': None
        }

        # Setup IB event handlers
        self._setup_ib_handlers()

    def _setup_ib_handlers(self):
        """Setup IB connection event handlers"""
        self.ib.connectedEvent += self._on_ib_connected
        self.ib.disconnectedEvent += self._on_ib_disconnected
        self.ib.errorEvent += self._on_ib_error

    def _on_ib_connected(self):
        """IB connection established event"""
        with self.lock:
            logger.info("✅ IB connection established")
            self.state = ConnectionState.CONNECTED
            self.retry_count = 0
            self.current_retry_delay = self.initial_retry_delay
            self.consecutive_failures = 0
            self.circuit_state = CircuitBreakerState.CLOSED
            self.last_heartbeat = datetime.now()

            self.stats['total_connections'] += 1
            self.stats['last_connected'] = datetime.now()
            if self.stats['uptime_start'] is None:
                self.stats['uptime_start'] = datetime.now()

            if self.on_connected:
                try:
                    self.on_connected()
                except Exception as e:
                    logger.error(f"Error in on_connected callback: {e}")

    def _on_ib_disconnected(self):
        """IB disconnection event"""
        with self.lock:
            if self.state == ConnectionState.CONNECTED:
                logger.warning("⚠️  IB connection lost")
                self.state = ConnectionState.DISCONNECTED
                self.stats['total_disconnections'] += 1
                self.stats['last_disconnected'] = datetime.now()

                if self.on_disconnected:
                    try:
                        self.on_disconnected()
                    except Exception as e:
                        logger.error(f"Error in on_disconnected callback: {e}")

                # Start reconnection if running
                if self.is_running:
                    self._start_reconnect()

    def _on_ib_error(self, reqId, errorCode, errorString, contract):
        """IB error event"""
        # Filter out informational messages
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection messages
            return

        if errorCode in [1100, 1101, 1102, 2110]:  # Connection lost/restored
            logger.warning(f"IB Connection warning {errorCode}: {errorString}")
        else:
            logger.error(f"IB Error {errorCode}: {errorString}")

        if self.on_error:
            try:
                self.on_error(Exception(f"IB Error {errorCode}: {errorString}"))
            except Exception as e:
                logger.error(f"Error in on_error callback: {e}")

    def connect(self) -> bool:
        """
        Connect to IB Gateway with automatic retry

        Returns:
            bool: True if connected successfully
        """
        with self.lock:
            if self.state == ConnectionState.CONNECTED:
                logger.info("Already connected to IB Gateway")
                return True

            self.state = ConnectionState.CONNECTING

        logger.info(f"🔗 Connecting to IB Gateway at {self.host}:{self.port} (client_id={self.client_id})")

        try:
            self.ib.connect(
                self.host,
                self.port,
                clientId=self.client_id,
                timeout=self.timeout
            )

            # Verify connection
            if self.ib.isConnected():
                accounts = self.ib.managedAccounts()
                logger.info(f"✅ Connected successfully - Accounts: {accounts}")
                return True
            else:
                raise Exception("Connection established but not in connected state")

        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            with self.lock:
                self.state = ConnectionState.DISCONNECTED
                self.consecutive_failures += 1
                self.stats['total_failures'] += 1

            if self.on_error:
                try:
                    self.on_error(e)
                except Exception as callback_error:
                    logger.error(f"Error in on_error callback: {callback_error}")

            return False

    def disconnect(self):
        """Disconnect from IB Gateway"""
        logger.info("Disconnecting from IB Gateway...")
        self.is_running = False

        # Stop threads
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)

        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2)

        # Disconnect IB
        try:
            if self.ib.isConnected():
                self.ib.disconnect()
            logger.info("✅ Disconnected successfully")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

        with self.lock:
            self.state = ConnectionState.DISCONNECTED

    def _start_reconnect(self):
        """Start reconnection thread"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return  # Already reconnecting

        logger.info("🔄 Starting reconnection thread...")
        self.state = ConnectionState.RECONNECTING
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
            name="IBReconnectThread"
        )
        self.reconnect_thread.start()

    def _reconnect_loop(self):
        """Reconnection loop with exponential backoff"""
        logger.info("🔄 Reconnection loop started")

        while self.is_running and self.state != ConnectionState.CONNECTED:
            # Check circuit breaker
            if self.circuit_state == CircuitBreakerState.OPEN:
                if self.circuit_opened_at:
                    elapsed = (datetime.now() - self.circuit_opened_at).total_seconds()
                    if elapsed < self.circuit_breaker_timeout:
                        remaining = self.circuit_breaker_timeout - elapsed
                        logger.warning(f"🔴 Circuit breaker OPEN - waiting {remaining:.0f}s before retry")
                        time.sleep(min(30, remaining))
                        continue
                    else:
                        logger.info("🟡 Circuit breaker entering HALF_OPEN state")
                        self.circuit_state = CircuitBreakerState.HALF_OPEN

            # Check max retries
            if self.max_retries > 0 and self.retry_count >= self.max_retries:
                logger.error(f"❌ Max retries ({self.max_retries}) reached. Giving up.")
                with self.lock:
                    self.state = ConnectionState.FAILED
                break

            # Wait before retry
            if self.retry_count > 0:
                logger.info(f"⏳ Waiting {self.current_retry_delay:.1f}s before retry {self.retry_count + 1}...")
                time.sleep(self.current_retry_delay)

            # Attempt reconnection
            logger.info(f"🔄 Reconnection attempt {self.retry_count + 1}" +
                       (f"/{self.max_retries}" if self.max_retries > 0 else ""))

            self.retry_count += 1
            success = self.connect()

            if success:
                logger.info("✅ Reconnection successful!")
                self.stats['total_reconnections'] += 1
                break
            else:
                # Update circuit breaker
                if self.consecutive_failures >= self.circuit_breaker_threshold:
                    if self.circuit_state != CircuitBreakerState.OPEN:
                        logger.error(f"🔴 Circuit breaker OPEN after {self.consecutive_failures} consecutive failures")
                        self.circuit_state = CircuitBreakerState.OPEN
                        self.circuit_opened_at = datetime.now()

                # Exponential backoff
                self.current_retry_delay = min(
                    self.current_retry_delay * 2,
                    self.max_retry_delay
                )

        logger.info("🔄 Reconnection loop ended")

    def start_monitoring(self):
        """Start connection monitoring and auto-reconnect"""
        self.is_running = True

        # Start heartbeat monitoring
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="IBHeartbeatThread"
        )
        self.heartbeat_thread.start()

        logger.info("📡 Connection monitoring started")

    def _heartbeat_loop(self):
        """Heartbeat monitoring loop"""
        logger.info("💓 Heartbeat monitoring started")

        while self.is_running:
            time.sleep(self.heartbeat_interval)

            if self.state == ConnectionState.CONNECTED:
                try:
                    # Check if still connected
                    if not self.ib.isConnected():
                        logger.warning("💔 Heartbeat failed - connection lost")
                        self._on_ib_disconnected()
                    else:
                        self.last_heartbeat = datetime.now()
                        logger.debug(f"💓 Heartbeat OK - {self.get_connection_info()}")

                except Exception as e:
                    logger.error(f"💔 Heartbeat check error: {e}")
                    self._on_ib_disconnected()

        logger.info("💓 Heartbeat monitoring stopped")

    def is_connected(self) -> bool:
        """Check if connected to IB"""
        return self.state == ConnectionState.CONNECTED and self.ib.isConnected()

    def get_ib(self) -> IB:
        """Get IB instance"""
        return self.ib

    def get_state(self) -> ConnectionState:
        """Get current connection state"""
        return self.state

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            'state': self.state.value,
            'circuit_state': self.circuit_state.value,
            'is_connected': self.is_connected(),
            'retry_count': self.retry_count,
            'consecutive_failures': self.consecutive_failures,
            'last_heartbeat': self.last_heartbeat,
            'stats': self.stats.copy()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = self.stats.copy()
        if stats['uptime_start']:
            stats['uptime_seconds'] = (datetime.now() - stats['uptime_start']).total_seconds()
        return stats

    def reset_stats(self):
        """Reset connection statistics"""
        with self.lock:
            self.stats = {
                'total_connections': 0,
                'total_disconnections': 0,
                'total_reconnections': 0,
                'total_failures': 0,
                'last_connected': None,
                'last_disconnected': None,
                'uptime_start': None
            }


# Convenience context manager
class IBConnection:
    """Context manager for IB connection with auto-reconnect"""

    def __init__(self, **kwargs):
        self.manager = IBConnectionManager(**kwargs)

    def __enter__(self):
        if not self.manager.connect():
            raise ConnectionError("Failed to connect to IB Gateway")
        self.manager.start_monitoring()
        return self.manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.disconnect()
        return False


if __name__ == "__main__":
    # Test the connection manager
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    def on_connected():
        logger.info("🎉 Connected callback triggered")

    def on_disconnected():
        logger.warning("⚠️  Disconnected callback triggered")

    def on_error(error):
        logger.error(f"❌ Error callback: {error}")

    # Test with context manager
    try:
        with IBConnection(
            host="127.0.0.1",
            port=4002,
            client_id=999,
            on_connected=on_connected,
            on_disconnected=on_disconnected,
            on_error=on_error
        ) as conn:
            logger.info(f"Connection info: {conn.get_connection_info()}")
            logger.info("Sleeping for 60 seconds to test connection...")
            time.sleep(60)
    except Exception as e:
        logger.error(f"Test failed: {e}")
