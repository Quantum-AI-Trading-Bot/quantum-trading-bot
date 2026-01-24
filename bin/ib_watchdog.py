#!/usr/bin/env python3
"""
Simple IB Watchdog for Isolation Testing
Runs alongside Gateway (without the trading bot) to isolate Gateway vs. Bot issues

Usage:
    python3 ib_watchdog.py

This will:
- Connect to IB Gateway with a unique client ID
- Subscribe to one stock ticker
- Log all IB error codes and disconnect events
- Stay connected and log any issues
"""

import sys
import time
import logging
import signal
from datetime import datetime
from ib_insync import *

# Add enhanced logging client
sys.path.append('/home/davidsanker/investor_bot_migration_20251017_163810/investor')
from ib_client_with_logging import IBClientWithLogging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/davidsanker/platform/logs/ib_watchdog.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ib_watchdog")

class IBWatchdog:
    """Simple IB connection watchdog for isolation testing"""

    def __init__(self, symbol="AAPL", client_id=999):
        self.symbol = symbol
        self.client_id = client_id
        self.ib_client = None
        self.ticker = None
        self.running = False
        self.last_data_time = None
        self.connection_time = None
        self.stats = {
            'data_updates': 0,
            'errors': 0,
            'disconnects': 0,
            'reconnections': 0,
            'start_time': datetime.now()
        }

    def start(self):
        """Start the watchdog"""
        logger.info(f"🐕 Starting IB Watchdog for {self.symbol}")
        self.running = True

        try:
            # Connect with enhanced logging
            self.ib_client = IBClientWithLogging()
            success = self.ib_client.connect("127.0.0.1", 4002, self.client_id)

            if not success:
                logger.error("❌ Failed to connect to IB Gateway")
                return False

            self.connection_time = datetime.now()
            logger.info("✅ Connected to IB Gateway")

            # Setup contract and subscribe to market data
            contract = Stock(self.symbol, "SMART", "USD")
            self.ib_client.ib.qualifyContracts(contract)

            self.ticker = self.ib_client.ib.reqMktData(contract, "", False, False)
            logger.info(f"📊 Subscribed to market data for {self.symbol}")

            # Setup event handlers
            self.ib_client.ib.pendingTickersEvent += self._on_pending_tickers

            # Start main loop
            self._main_loop()

        except Exception as e:
            logger.error(f"❌ Watchdog failed: {e}")
            self.running = False

    def _on_pending_tickers(self, tickers):
        """Handle market data updates"""
        for ticker in tickers:
            if ticker.last:
                self.last_data_time = datetime.now()
                self.stats['data_updates'] += 1

                # Log data updates periodically (not too spammy)
                if self.stats['data_updates'] % 100 == 0:
                    logger.info(f"📈 {self.symbol} last: {ticker.last:.2f} (update #{self.stats['data_updates']})")

    def _main_loop(self):
        """Main monitoring loop"""
        logger.info("🔄 Watchdog monitoring started")

        try:
            while self.running:
                # Check connection health
                if not self.ib_client.ib.isConnected():
                    logger.error("❌ Connection lost!")
                    self.stats['disconnects'] += 1
                    self._attempt_reconnection()
                    continue

                # Check for data staleness
                if self.last_data_time:
                    data_age = datetime.now() - self.last_data_time
                    if data_age.total_seconds() > 300:  # 5 minutes without data
                        logger.warning(f"⚠️  No data for {int(data_age.total_seconds())} seconds")

                # Log status periodically
                self._log_status()

                # Wait before next check
                time.sleep(30)

        except KeyboardInterrupt:
            logger.info("🛑 Watchdog stopped by user")
        except Exception as e:
            logger.error(f"❌ Watchdog loop error: {e}")
        finally:
            self._cleanup()

    def _attempt_reconnection(self):
        """Attempt to reconnect to Gateway"""
        logger.info("🔄 Attempting reconnection...")
        self.stats['reconnections'] += 1

        try:
            # Disconnect first
            if self.ib_client:
                self.ib_client.disconnect()

            # Wait a bit
            time.sleep(10)

            # Reconnect
            self.ib_client = IBClientWithLogging()
            success = self.ib_client.connect("127.0.0.1", 4002, self.client_id + 1)

            if success:
                logger.info("✅ Reconnected successfully")
                self.connection_time = datetime.now()

                # Resubscribe to data
                contract = Stock(self.symbol, "SMART", "USD")
                self.ib_client.ib.qualifyContracts(contract)
                self.ticker = self.ib_client.ib.reqMktData(contract, "", False, False)
                self.ib_client.ib.pendingTickersEvent += self._on_pending_tickers

            else:
                logger.error("❌ Reconnection failed")

        except Exception as e:
            logger.error(f"❌ Reconnection attempt failed: {e}")

    def _log_status(self):
        """Log periodic status"""
        runtime = datetime.now() - self.stats['start_time']

        # Log every 10 minutes
        if int(runtime.total_seconds()) % 600 == 0:
            uptime = str(runtime).split('.')[0]  # Remove microseconds

            status_msg = (
                f"📊 Status [{uptime}]: "
                f"Updates: {self.stats['data_updates']}, "
                f"Errors: {self.stats['errors']}, "
                f"Disconnects: {self.stats['disconnects']}, "
                f"Reconnections: {self.stats['reconnections']}"
            )

            if self.ib_client and self.ib_client.ib.isConnected():
                # Get connection stats from enhanced client
                conn_stats = self.ib_client.get_connection_stats()
                status_msg += f", IB Stats: {conn_stats.get('total_events', 0)} events"

            logger.info(status_msg)

    def _cleanup(self):
        """Clean shutdown"""
        logger.info("🧹 Cleaning up...")
        self.running = False

        if self.ib_client:
            self.ib_client.disconnect()

        # Final statistics
        runtime = datetime.now() - self.stats['start_time']
        logger.info("=" * 60)
        logger.info("📊 FINAL WATCHDOG STATISTICS")
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Data Updates: {self.stats['data_updates']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Disconnects: {self.stats['disconnects']}")
        logger.info(f"Reconnections: {self.stats['reconnections']}")
        logger.info("=" * 60)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

def main():
    """Main function"""
    logger.info("🚀 IB Watchdog - Isolation Testing Tool")
    logger.info("This tool helps isolate Gateway issues from Bot issues")
    logger.info("Run this overnight without your trading bot to see Gateway stability")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start watchdog
    watchdog = IBWatchdog(symbol="AAPL", client_id=999)

    try:
        watchdog.start()
    except Exception as e:
        logger.error(f"Watchdog failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()