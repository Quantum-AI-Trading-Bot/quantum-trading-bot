#!/usr/bin/env python3
"""
Robust IB Gateway Connection Monitor with Auto-Recovery
Addresses chronic authentication and disconnect issues
"""

import os
import sys
import time
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from ib_insync import IB, util

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/davidsanker/platform/logs/robust_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RobustConnectionMonitor:
    """Enhanced connection monitor with proactive recovery"""

    def __init__(self):
        self.ib = IB()
        self.monitoring = False
        self.last_health_check = 0
        self.connection_attempts = 0
        self.max_attempts = 3
        self.health_interval = 30  # seconds
        self.last_success = None
        self.stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failures': 0,
            'reconnections': 0,
            'last_failure': None
        }

    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitoring:
            logger.warning("Monitoring already active")
            return

        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("🔍 Robust connection monitoring started")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.ib.isConnected():
            self.ib.disconnect()
        logger.info("Monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Monitor loop initiated")

        while self.monitoring:
            try:
                self._perform_health_check()
                time.sleep(self.health_interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(10)

    def _perform_health_check(self):
        """Comprehensive health check with recovery"""
        self.stats['total_checks'] += 1
        current_time = datetime.now()

        # Check if connected
        if not self.ib.isConnected():
            logger.warning("🔌 IB Gateway disconnected - attempting reconnection")
            self._attempt_reconnection()
            return

        # Deeper health check
        try:
            # Test account data request
            self.ib.reqAccountSummary(9001, "All", "$LEDGER")
            time.sleep(1)
            self.ib.cancelAccountSummary(9001)

            # Update success stats
            self.stats['successful_checks'] += 1
            self.last_success = current_time
            self.connection_attempts = 0

            logger.debug(f"✅ Connection healthy - {self.stats['successful_checks']}/{self.stats['total_checks']} checks successful")

        except Exception as e:
            logger.warning(f"⚠️  Health check failed: {e}")
            self.stats['failures'] += 1
            self.stats['last_failure'] = current_time.isoformat()

            # Trigger recovery if multiple failures
            if self.connection_attempts >= self.max_attempts:
                logger.error(f"❌ Too many failures ({self.connection_attempts}) - triggering recovery")
                self._trigger_recovery()
            else:
                self.connection_attempts += 1
                self._attempt_reconnection()

    def _attempt_reconnection(self):
        """Attempt to reconnect to IB Gateway"""
        if self.connection_attempts >= self.max_attempts:
            logger.warning("Max reconnection attempts reached - triggering recovery")
            self._trigger_recovery()
            return

        try:
            # Disconnect first
            if self.ib.isConnected():
                self.ib.disconnect()
                time.sleep(2)

            # Attempt connection
            self.ib.connect('127.0.0.1', 4002, clientId=int(time.time()) % 1000, timeout=10)

            if self.ib.isConnected():
                logger.info("🔄 Reconnection successful")
                self.stats['reconnections'] += 1
                self.connection_attempts = 0
                return True
            else:
                logger.error("❌ Reconnection failed")
                self.connection_attempts += 1
                return False

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            self.connection_attempts += 1
            return False

    def _trigger_recovery(self):
        """Trigger full recovery sequence"""
        logger.info("🚨 TRIGGERING FULL RECOVERY SEQUENCE")

        try:
            # Step 1: Disconnect
            if self.ib.isConnected():
                self.ib.disconnect()

            # Step 2: Reset connection attempt counter
            self.connection_attempts = 0

            # Step 3: Check if Gateway process is running
            gateway_running = self._check_gateway_process()

            if not gateway_running:
                logger.warning("IB Gateway process not found - attempting restart")
                self._restart_gateway()

            # Step 4: Wait and test connection
            time.sleep(30)  # Wait for Gateway to initialize

            # Step 5: Attempt reconnection
            if self._attempt_reconnection():
                logger.info("✅ Recovery successful")
            else:
                logger.error("❌ Recovery failed - manual intervention required")
                logger.error("Please access VNC and check IB Gateway status")

        except Exception as e:
            logger.error(f"Recovery sequence failed: {e}")

    def _check_gateway_process(self):
        """Check if IB Gateway process is running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'ibgateway'],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _restart_gateway(self):
        """Attempt to restart IB Gateway"""
        logger.info("Attempting to restart IB Gateway...")

        try:
            # Kill existing processes
            subprocess.run(['pkill', '-f', 'java'], check=False)
            time.sleep(3)

            # Start new Gateway
            subprocess.Popen([
                'DISPLAY=:1',
                '/home/davidsanker/IBGateway/ibgateway.bin'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            logger.info("Gateway restart initiated")

        except Exception as e:
            logger.error(f"Gateway restart failed: {e}")

    def get_status(self):
        """Get comprehensive monitoring status"""
        uptime_percentage = 0
        if self.stats['total_checks'] > 0:
            uptime_percentage = (self.stats['successful_checks'] / self.stats['total_checks']) * 100

        return {
            'monitoring_active': self.monitoring,
            'ib_connected': self.ib.isConnected(),
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'connection_attempts': self.connection_attempts,
            'uptime_percentage': round(uptime_percentage, 2),
            'stats': self.stats.copy()
        }

def main():
    """Main function to run the monitor"""
    logger.info("🚀 Starting Robust IB Gateway Connection Monitor")

    monitor = RobustConnectionMonitor()

    try:
        # Start monitoring
        monitor.start_monitoring()

        # Keep running
        logger.info("Monitor is running... Press Ctrl+C to stop")

        while True:
            time.sleep(60)
            status = monitor.get_status()

            # Log status every 5 minutes
            if status['total_checks'] % 10 == 0:
                logger.info(f"Status: {status['uptime_percentage']}% uptime, "
                          f"{status['stats']['reconnections']} reconnections")

    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
        monitor.stop_monitoring()

    except Exception as e:
        logger.error(f"Monitor crashed: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()