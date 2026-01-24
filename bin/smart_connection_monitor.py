#!/usr/bin/env python3
"""
Smart IB Gateway Connection Monitor with Failure Classification
Classifies different failure modes and applies appropriate recovery strategies
"""

import os
import sys
import time
import subprocess
import threading
import logging
import json
import signal
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from ib_insync import IB

# Add project path
sys.path.append('/home/davidsanker/investor_bot_migration_20251017_163810/investor')
from ib_client_with_logging import IBClientWithLogging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/davidsanker/platform/logs/smart_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SmartConnectionMonitor:
    """
    Intelligent connection monitor that classifies failures and applies appropriate recovery
    """

    def __init__(self):
        self.ib_client = None
        self.monitoring = False
        self.failure_counter = 0
        self.max_failures = 3
        self.health_interval = 30  # seconds

        # Failure state tracking
        self.last_failure_time = None
        self.last_error_code = None
        self.gateway_restarts = 0
        self.last_gateway_restart = None

        # State file for persistence
        self.state_file = "/home/davidsanker/platform/logs/monitor_state.json"

        # Recovery limits
        self.max_gateway_restarts_per_hour = 2
        self.restart_cooldown_minutes = 5

        # Load previous state
        self._load_state()

    def _load_state(self):
        """Load monitor state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.gateway_restarts = state.get('gateway_restarts', 0)
                    self.last_gateway_restart = state.get('last_gateway_restart')
                    logger.info(f"Loaded state: {self.gateway_restarts} previous restarts")
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Save monitor state to file"""
        try:
            state = {
                'gateway_restarts': self.gateway_restarts,
                'last_gateway_restart': self.last_gateway_restart,
                'last_save': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def start_monitoring(self):
        """Start the smart monitoring loop"""
        if self.monitoring:
            logger.warning("Smart monitoring already active")
            return

        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("🧠 Smart connection monitoring started")

    def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        self.monitoring = False
        if self.ib_client:
            self.ib_client.disconnect()
        logger.info("Smart monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop with intelligent failure classification"""
        logger.info("Smart monitor loop initiated")

        while self.monitoring:
            try:
                health_status = self._perform_comprehensive_health_check()

                # Log status periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    logger.info(f"Status: {health_status}")

                time.sleep(self.health_interval)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(10)

    def _perform_comprehensive_health_check(self) -> Dict:
        """
        Comprehensive health check that classifies failure modes
        Returns: Dict with health status and classification
        """
        try:
            # 1. Check Gateway Process
            gateway_status = self._check_gateway_process()

            # 2. Check Port Accessibility
            port_status = self._check_port_status()

            # 3. Check API Connection
            api_status = self._check_api_connection()

            # 4. Classify overall status
            if api_status['connected']:
                # API working - all good
                self._reset_failure_state()
                return {
                    'status': 'HEALTHY',
                    'gateway': gateway_status,
                    'port': port_status,
                    'api': api_status,
                    'action': 'NONE'
                }

            # API not working - classify the problem
            classification = self._classify_failure(gateway_status, port_status, api_status)
            action = self._apply_recovery_strategy(classification)

            return {
                'status': 'ISSUE_DETECTED',
                'classification': classification,
                'gateway': gateway_status,
                'port': port_status,
                'api': api_status,
                'action': action
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'CHECK_ERROR',
                'error': str(e),
                'action': 'RETRY'
            }

    def _check_gateway_process(self) -> Dict:
        """Check IB Gateway process health"""
        try:
            result = subprocess.run(['pgrep', '-f', 'ibgateway'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]

                # Check process age
                oldest_pid = min(pids)
                try:
                    # Get process start time
                    stat_result = subprocess.run(
                        ['ps', '-o', 'lstart=', '-p', str(oldest_pid)],
                        capture_output=True, text=True
                    )
                    start_time = stat_result.stdout.strip()
                    return {
                        'running': True,
                        'pids': pids,
                        'oldest_start': start_time,
                        'pid_count': len(pids)
                    }
                except:
                    return {'running': True, 'pids': pids}
            else:
                return {'running': False, 'pids': []}

        except Exception as e:
            return {'running': 'ERROR', 'error': str(e)}

    def _check_port_status(self) -> Dict:
        """Check if port 4002 is accessible"""
        try:
            # Check if port is listening
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)

            port_listening = '4002' in result.stdout

            if port_listening:
                # Try to extract PID
                for line in result.stdout.split('\n'):
                    if '4002' in line:
                        parts = line.split()
                        if len(parts) > 6 and parts[-1].isdigit():
                            pid = int(parts[-1])
                            return {
                                'listening': True,
                                'pid': pid,
                                'accessible': self._test_port_connectivity()
                            }

                return {'listening': True, 'accessible': self._test_port_connectivity()}
            else:
                return {'listening': False}

        except Exception as e:
            return {'listening': 'ERROR', 'error': str(e)}

    def _test_port_connectivity(self) -> bool:
        """Test if we can actually connect to port 4002"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('127.0.0.1', 4002))
            sock.close()
            return result == 0
        except:
            return False

    def _check_api_connection(self) -> Dict:
        """Check IB API connection health"""
        try:
            if not self.ib_client:
                self.ib_client = IBClientWithLogging()

            # Quick connection test
            if self.ib_client.is_healthy():
                return {
                    'connected': True,
                    'last_error': self.ib_client.get_last_error(),
                    'connection_stats': self.ib_client.get_connection_stats()
                }
            else:
                # Try to connect
                if self.ib_client.connect(timeout=5):
                    return {
                        'connected': True,
                        'last_error': None,
                        'connection_stats': self.ib_client.get_connection_stats()
                    }
                else:
                    return {
                        'connected': False,
                        'last_error': self.ib_client.get_last_error(),
                        'connection_stats': self.ib_client.get_connection_stats()
                    }

        except Exception as e:
            return {'connected': 'ERROR', 'error': str(e)}

    def _classify_failure(self, gateway: Dict, port: Dict, api: Dict) -> str:
        """
        Classify the type of failure based on system state

        Returns one of:
        - GATEWAY_DEAD: No Gateway process running
        - GATEWAY_DEADLOCK: Gateway running but not responding
        - PORT_CLOSED: Port not listening
        - API_AUTH: Authentication/2FA issues
        - API_PACING: Rate limiting violations
        - IB_NETWORK: IB connectivity issues (1100, 1101, 1102)
        - UNKNOWN: Unclassified issue
        """
        if not gateway.get('running', False):
            return 'GATEWAY_DEAD'

        if not port.get('listening', False):
            return 'PORT_CLOSED'

        if not port.get('accessible', False):
            return 'GATEWAY_DEADLOCK'

        # Check API-specific errors
        last_error = api.get('last_error')
        if last_error:
            error_code = last_error.get('errorCode')
            if error_code == 100:
                return 'API_PACING'
            elif error_code in [1100, 1101, 1102]:
                return 'IB_NETWORK'
            elif error_code in [1300]:
                return 'PORT_RESET'

        # If gateway is running but API fails, likely auth/2FA
        if gateway.get('running') and port.get('listening') and not api.get('connected'):
            return 'API_AUTH'

        return 'UNKNOWN'

    def _apply_recovery_strategy(self, classification: str) -> str:
        """
        Apply appropriate recovery strategy based on failure classification
        """
        self.failure_counter += 1
        self.last_failure_time = datetime.now()

        if self.failure_counter < self.max_failures:
            logger.warning(f"Failure #{self.failure_counter}/{self.max_failures}: {classification}")
            return 'MONITORING'

        # Apply recovery based on classification
        if classification == 'GATEWAY_DEAD':
            return self._restart_gateway()

        elif classification == 'GATEWAY_DEADLOCK':
            logger.warning("Gateway appears deadlocked - attempting force restart")
            return self._restart_gateway(force=True)

        elif classification in ['PORT_CLOSED', 'PORT_RESET']:
            logger.warning("Port issue detected - restarting Gateway")
            return self._restart_gateway()

        elif classification == 'API_PACING':
            logger.error("API pacing violation detected - throttling bot, not Gateway")
            return 'THROTTLE_BOT'

        elif classification == 'IB_NETWORK':
            logger.warning("IB network connectivity issue - attempting restart")
            return self._restart_gateway()

        elif classification == 'API_AUTH':
            logger.error("Authentication/2FA issue detected - manual intervention required")
            logger.error("Please check VNC and complete 2FA if needed")
            return 'MANUAL_AUTH_REQUIRED'

        else:  # UNKNOWN
            logger.warning("Unknown failure type - attempting Gateway restart as fallback")
            return self._restart_gateway()

    def _restart_gateway(self, force: bool = False) -> str:
        """
        Restart IB Gateway with cooldown protection
        """
        current_time = datetime.now()

        # Check if we've restarted too recently
        if (self.last_gateway_restart and
            (current_time - datetime.fromisoformat(self.last_gateway_restart)).seconds < self.restart_cooldown_minutes * 60):
            logger.warning(f"Gateway restart cooldown active - waiting {self.restart_cooldown_minutes} minutes")
            return 'COOLDOWN_ACTIVE'

        # Check restart rate limit
        restarts_this_hour = self._count_recent_restarts()
        if restarts_this_hour >= self.max_gateway_restarts_per_hour:
            logger.error(f"Too many Gateway restarts this hour ({restarts_this_hour})")
            return 'RATE_LIMIT_EXCEEDED'

        logger.info(f"🔄 Restarting IB Gateway (classification: {classification if 'classification' in locals() else 'forced'})")

        try:
            # Kill processes
            if force:
                subprocess.run(['pkill', '-9', '-f', 'java'], check=False)
            else:
                subprocess.run(['pkill', '-f', 'ibgateway'], check=False)

            time.sleep(3)

            # Clean temp files
            subprocess.run(['rm', '-f', '/home/davidsanker/IBGateway/*.tmp', '/home/davidsanker/IBGateway/*.lock'],
                         check=False)

            # Start Gateway via IBC
            subprocess.run([
                '/home/davidsanker/IBC/scripts/ibcstart.sh'
            ], check=False)

            # Update state
            self.gateway_restarts += 1
            self.last_gateway_restart = current_time.isoformat()
            self._save_state()

            logger.info(f"Gateway restart initiated (#{self.gateway_restarts} total)")
            return 'GATEWAY_RESTARTED'

        except Exception as e:
            logger.error(f"Gateway restart failed: {e}")
            return 'RESTART_FAILED'

    def _count_recent_restarts(self) -> int:
        """Count Gateway restarts in the last hour"""
        if not self.last_gateway_restart:
            return 0

        try:
            last_restart = datetime.fromisoformat(self.last_gateway_restart)
            if (datetime.now() - last_restart).seconds < 3600:  # Within last hour
                return 1
            return 0
        except:
            return 0

    def _reset_failure_state(self):
        """Reset failure counters on successful connection"""
        if self.failure_counter > 0:
            logger.info(f"✅ Connection restored after {self.failure_counter} failures")
        self.failure_counter = 0
        self.last_failure_time = None

    def get_status(self) -> Dict:
        """Get comprehensive monitor status"""
        current_time = datetime.now()

        status = {
            'monitoring_active': self.monitoring,
            'failure_counter': self.failure_counter,
            'gateway_restarts': self.gateway_restarts,
            'last_gateway_restart': self.last_gateway_restart,
            'uptime_percentage': 0,
            'last_health_check': current_time.isoformat()
        }

        # Add API connection stats if available
        if self.ib_client:
            status['api_stats'] = self.ib_client.get_connection_stats()

        return status

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal - stopping monitor")
    sys.exit(0)

def main():
    """Main function"""
    logger.info("🚀 Starting Smart IB Gateway Connection Monitor")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start monitor
    monitor = SmartConnectionMonitor()

    try:
        monitor.start_monitoring()

        # Keep running and log status periodically
        while True:
            time.sleep(60)  # Status update every minute
            status = monitor.get_status()
            logger.info(f"Monitor status: {status['failure_counter']} failures, {status['gateway_restarts']} restarts")

    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
        monitor.stop_monitoring()

    except Exception as e:
        logger.error(f"Monitor crashed: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()