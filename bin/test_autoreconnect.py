#!/usr/bin/env python3
"""
Auto-Reconnect Test Script
Tests the automatic reconnection mechanism by simulating disconnections

This script will:
1. Connect to IB Gateway
2. Verify connection is established
3. Simulate disconnect by killing the connection
4. Verify auto-reconnect works
5. Report results

Author: David Sanker
Date: January 28, 2026
"""

import sys
import time
import logging
from datetime import datetime

# Add paths
sys.path.insert(0, '/home/davidsanker/platform')
sys.path.insert(0, '/home/davidsanker/platform/utils')

from ib_connection_manager import IBConnectionManager, ConnectionState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
TEST_CLIENT_ID = 996
HEARTBEAT_INTERVAL = 10
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2.0


class AutoReconnectTester:
    """Test auto-reconnect functionality"""

    def __init__(self):
        self.test_results = []
        self.connection_manager = None

    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name} - {message}")
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now()
        })

    def test_initial_connection(self):
        """Test 1: Initial connection establishment"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Initial Connection")
        logger.info("=" * 60)

        try:
            self.connection_manager = IBConnectionManager(
                host=IB_HOST,
                port=IB_PORT,
                client_id=TEST_CLIENT_ID,
                timeout=15,
                max_retries=MAX_RETRIES,
                initial_retry_delay=INITIAL_RETRY_DELAY,
                heartbeat_interval=HEARTBEAT_INTERVAL,
                on_connected=lambda: logger.info("🎉 Connected callback triggered"),
                on_disconnected=lambda: logger.warning("⚠️  Disconnected callback triggered"),
                on_error=lambda e: logger.error(f"❌ Error callback: {e}")
            )

            # Attempt connection
            success = self.connection_manager.connect()

            if success and self.connection_manager.is_connected():
                self.log_test("Initial Connection", True, "Connected successfully")
                return True
            else:
                self.log_test("Initial Connection", False, "Failed to connect")
                return False

        except Exception as e:
            self.log_test("Initial Connection", False, f"Exception: {e}")
            return False

    def test_heartbeat_monitoring(self):
        """Test 2: Heartbeat monitoring"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Heartbeat Monitoring")
        logger.info("=" * 60)

        try:
            # Start monitoring
            self.connection_manager.start_monitoring()

            # Wait for a few heartbeats
            logger.info(f"Waiting {HEARTBEAT_INTERVAL * 2} seconds for heartbeats...")
            time.sleep(HEARTBEAT_INTERVAL * 2)

            # Check if still connected
            if self.connection_manager.is_connected():
                info = self.connection_manager.get_connection_info()
                last_hb = info.get('last_heartbeat')
                if last_hb:
                    self.log_test("Heartbeat Monitoring", True,
                                f"Last heartbeat: {last_hb.strftime('%H:%M:%S')}")
                    return True
                else:
                    self.log_test("Heartbeat Monitoring", False, "No heartbeat recorded")
                    return False
            else:
                self.log_test("Heartbeat Monitoring", False, "Connection lost during heartbeat")
                return False

        except Exception as e:
            self.log_test("Heartbeat Monitoring", False, f"Exception: {e}")
            return False

    def test_manual_disconnect_reconnect(self):
        """Test 3: Manual disconnect and auto-reconnect"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Manual Disconnect and Auto-Reconnect")
        logger.info("=" * 60)

        try:
            # Manually disconnect
            logger.info("📡 Manually disconnecting...")
            ib = self.connection_manager.get_ib()
            ib.disconnect()

            # Wait a moment
            time.sleep(2)

            # Check if reconnect was triggered
            state = self.connection_manager.get_state()
            logger.info(f"State after disconnect: {state.value}")

            # Wait for reconnection
            max_wait = 60  # Wait up to 60 seconds
            waited = 0
            reconnected = False

            logger.info(f"Waiting up to {max_wait}s for auto-reconnect...")

            while waited < max_wait:
                if self.connection_manager.is_connected():
                    reconnected = True
                    break

                time.sleep(5)
                waited += 5
                state = self.connection_manager.get_state()
                logger.info(f"  [{waited}s] State: {state.value}")

            if reconnected:
                stats = self.connection_manager.get_stats()
                reconnections = stats.get('total_reconnections', 0)
                self.log_test("Auto-Reconnect", True,
                            f"Reconnected after {waited}s (total reconnects: {reconnections})")
                return True
            else:
                self.log_test("Auto-Reconnect", False,
                            f"Failed to reconnect within {max_wait}s")
                return False

        except Exception as e:
            self.log_test("Auto-Reconnect", False, f"Exception: {e}")
            return False

    def test_connection_stats(self):
        """Test 4: Connection statistics tracking"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Connection Statistics")
        logger.info("=" * 60)

        try:
            stats = self.connection_manager.get_stats()
            info = self.connection_manager.get_connection_info()

            logger.info("📊 Connection Statistics:")
            logger.info(f"   Total Connections: {stats.get('total_connections', 0)}")
            logger.info(f"   Total Reconnections: {stats.get('total_reconnections', 0)}")
            logger.info(f"   Total Disconnections: {stats.get('total_disconnections', 0)}")
            logger.info(f"   Total Failures: {stats.get('total_failures', 0)}")

            if 'uptime_seconds' in stats:
                logger.info(f"   Uptime: {stats['uptime_seconds']:.1f} seconds")

            logger.info(f"   Current State: {info.get('state', 'unknown')}")
            logger.info(f"   Circuit Breaker: {info.get('circuit_state', 'unknown')}")

            # Verify we have some activity
            if stats.get('total_connections', 0) > 0:
                self.log_test("Connection Statistics", True, "Stats tracked correctly")
                return True
            else:
                self.log_test("Connection Statistics", False, "No connections recorded")
                return False

        except Exception as e:
            self.log_test("Connection Statistics", False, f"Exception: {e}")
            return False

    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)

        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            logger.info(f"{status} {result['test']}: {result['message']}")

        logger.info("=" * 60)
        logger.info(f"Results: {passed}/{total} tests passed")

        if passed == total:
            logger.info("✅ ALL TESTS PASSED!")
            return True
        else:
            logger.info("❌ SOME TESTS FAILED")
            return False

    def cleanup(self):
        """Cleanup resources"""
        logger.info("\n🧹 Cleaning up...")
        if self.connection_manager:
            try:
                self.connection_manager.disconnect()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 AUTO-RECONNECT TEST SUITE")
        logger.info("=" * 60)
        logger.info(f"Target: {IB_HOST}:{IB_PORT}")
        logger.info(f"Client ID: {TEST_CLIENT_ID}")
        logger.info("=" * 60)

        try:
            # Run tests
            if not self.test_initial_connection():
                logger.error("Initial connection failed - aborting remaining tests")
                return False

            self.test_heartbeat_monitoring()
            self.test_manual_disconnect_reconnect()
            self.test_connection_stats()

            # Print summary
            return self.print_summary()

        finally:
            self.cleanup()


def main():
    """Entry point"""
    tester = AutoReconnectTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
