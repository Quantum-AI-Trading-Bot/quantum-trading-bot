#!/usr/bin/env python3
"""
Quantum Trading Bot with Auto-Reconnect
Wrapper that adds resilient connection management to the quantum trading bot

Features:
- Automatic reconnection on disconnect
- Health monitoring with heartbeat
- Connection statistics and logging
- Graceful degradation on repeated failures

Author: David Sanker
Date: January 28, 2026
"""

import os
import sys
import time
import logging
import signal
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, '/home/davidsanker/quantum-trading-bot-new')
sys.path.insert(0, '/home/davidsanker/platform')
sys.path.insert(0, '/home/davidsanker/platform/utils')

from ib_connection_manager import IBConnectionManager, ConnectionState

# Setup logging
log_dir = "/home/davidsanker/platform/logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/quantum-trading-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
CLIENT_ID = 403  # Unique client ID for auto-reconnect bot
HEARTBEAT_INTERVAL = 30  # Check connection every 30 seconds
MAX_RETRIES = -1  # Infinite retries
INITIAL_RETRY_DELAY = 5.0  # Start with 5 second delay
MAX_RETRY_DELAY = 300.0  # Max 5 minutes between retries
CIRCUIT_BREAKER_THRESHOLD = 10  # Open circuit after 10 failures
CIRCUIT_BREAKER_TIMEOUT = 600  # Wait 10 minutes before retrying


class QuantumBotWithAutoReconnect:
    """Quantum Trading Bot with automatic reconnection"""

    def __init__(self):
        self.is_running = False
        self.connection_manager = None
        self.trading_bot = None

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.is_running = False
        if self.connection_manager:
            self.connection_manager.disconnect()
        sys.exit(0)

    def _on_connected(self):
        """Called when connection is established"""
        logger.info("🎉 Connection established - starting trading operations")
        self._log_connection_stats()

        # Initialize trading bot if needed
        if self.trading_bot is None:
            self._initialize_trading_bot()

    def _on_disconnected(self):
        """Called when connection is lost"""
        logger.warning("⚠️  Connection lost - trading operations paused")
        logger.info("🔄 Auto-reconnect will attempt to restore connection...")

    def _on_error(self, error: Exception):
        """Called when connection error occurs"""
        logger.error(f"❌ Connection error: {error}")

    def _initialize_trading_bot(self):
        """Initialize the quantum trading bot with connection manager's IB instance"""
        try:
            logger.info("🚀 Initializing Quantum Trading Bot...")

            # Import the actual quantum bot
            from quantum_trading_bot import QuantumTradingBot

            # Create bot instance
            self.trading_bot = QuantumTradingBot()

            # Replace IB instance with our managed connection
            self.trading_bot.ib = self.connection_manager.get_ib()

            logger.info("✅ Quantum Trading Bot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {e}")
            logger.error("Will retry on next connection cycle")

    def _log_connection_stats(self):
        """Log connection statistics"""
        try:
            stats = self.connection_manager.get_stats()
            info = self.connection_manager.get_connection_info()

            logger.info("📊 Connection Statistics:")
            logger.info(f"   Total Connections: {stats.get('total_connections', 0)}")
            logger.info(f"   Total Reconnections: {stats.get('total_reconnections', 0)}")
            logger.info(f"   Total Disconnections: {stats.get('total_disconnections', 0)}")
            logger.info(f"   Total Failures: {stats.get('total_failures', 0)}")

            if 'uptime_seconds' in stats:
                uptime_hours = stats['uptime_seconds'] / 3600
                logger.info(f"   Uptime: {uptime_hours:.1f} hours")

            logger.info(f"   State: {info.get('state', 'unknown')}")
            logger.info(f"   Circuit Breaker: {info.get('circuit_state', 'unknown')}")

        except Exception as e:
            logger.error(f"Error logging stats: {e}")

    def run(self):
        """Main run loop"""
        logger.info("=" * 80)
        logger.info("🚀 QUANTUM TRADING BOT WITH AUTO-RECONNECT")
        logger.info("=" * 80)
        logger.info("⚛️  Quantum Stack: ACTIVE")
        logger.info("🔄 Auto-Reconnect: ENABLED")
        logger.info("💓 Heartbeat Monitoring: ENABLED")
        logger.info("🔴 Circuit Breaker: ENABLED")
        logger.info(f"🔗 Target: {IB_HOST}:{IB_PORT}")
        logger.info("=" * 80)

        # Create connection manager
        self.connection_manager = IBConnectionManager(
            host=IB_HOST,
            port=IB_PORT,
            client_id=CLIENT_ID,
            timeout=15,
            max_retries=MAX_RETRIES,
            initial_retry_delay=INITIAL_RETRY_DELAY,
            max_retry_delay=MAX_RETRY_DELAY,
            heartbeat_interval=HEARTBEAT_INTERVAL,
            circuit_breaker_threshold=CIRCUIT_BREAKER_THRESHOLD,
            circuit_breaker_timeout=CIRCUIT_BREAKER_TIMEOUT,
            on_connected=self._on_connected,
            on_disconnected=self._on_disconnected,
            on_error=self._on_error
        )

        # Initial connection
        logger.info("🔗 Establishing initial connection...")
        if not self.connection_manager.connect():
            logger.error("❌ Initial connection failed")
            logger.info("🔄 Auto-reconnect will continue trying in background...")

        # Start monitoring
        self.connection_manager.start_monitoring()
        self.is_running = True

        logger.info("✅ Connection manager started")
        logger.info("📡 Monitoring and auto-reconnect are active")

        # Main loop
        last_stats_log = time.time()
        stats_log_interval = 3600  # Log stats every hour

        try:
            while self.is_running:
                # Check if we need to initialize trading bot
                if (self.connection_manager.is_connected() and
                    self.trading_bot is None):
                    self._initialize_trading_bot()

                # Run trading cycle if connected
                if (self.connection_manager.is_connected() and
                    self.trading_bot is not None):
                    try:
                        # Run one trading cycle
                        self.trading_bot.run_cycle()

                    except Exception as e:
                        logger.error(f"Error in trading cycle: {e}")
                        logger.info("Will retry on next cycle")

                else:
                    # Not connected - wait for reconnection
                    if self.connection_manager.get_state() == ConnectionState.FAILED:
                        logger.error("❌ Connection manager in FAILED state - exiting")
                        break

                    logger.info(f"⏳ Waiting for connection (state: {self.connection_manager.get_state().value})...")
                    time.sleep(10)

                # Periodically log stats
                if time.time() - last_stats_log > stats_log_interval:
                    self._log_connection_stats()
                    last_stats_log = time.time()

                # Sleep between cycles
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            logger.info("Shutting down...")
            if self.connection_manager:
                self._log_connection_stats()
                self.connection_manager.disconnect()
            logger.info("Shutdown complete")


def main():
    """Entry point"""
    bot = QuantumBotWithAutoReconnect()
    bot.run()


if __name__ == "__main__":
    main()
