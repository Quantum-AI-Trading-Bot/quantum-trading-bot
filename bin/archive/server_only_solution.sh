#!/bin/bash
set -euo pipefail

# ============================================================================
# SERVER-SIDE ONLY SOLUTION: No GUI Automation Required
# Pure monitoring + alerting + graceful degradation
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/server-only"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/server_solution_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Create server-side monitoring system
create_server_monitor() {
    log "Creating server-side monitoring system..."

    cat > /home/davidsanker/platform/bin/server_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Server-Side IB Gateway Monitor
No GUI automation - pure monitoring + alerting
"""

import os
import time
import json
import logging
import subprocess
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from ib_insync import IB, util

class IBServerMonitor:
    def __init__(self):
        self.log_dir = "/home/davidsanker/platform/logs/server-only"
        os.makedirs(self.log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(f'{self.log_dir}/monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.status_file = f'{self.log_dir}/status.json'
        self.alerts_file = f'{self.log_dir}/alerts.json'

    def check_process_health(self) -> Dict:
        """Check if IB Gateway process is running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'java.*ibgateway'],
                                  capture_output=True, text=True)
            pids = result.stdout.strip().split('\n') if result.stdout.strip() else []

            return {
                'process_running': len(pids) > 0,
                'pids': pids,
                'process_count': len(pids)
            }
        except Exception as e:
            self.logger.error(f"Process check failed: {e}")
            return {'process_running': False, 'pids': [], 'error': str(e)}

    def check_port_health(self) -> Dict:
        """Check if port 4002 is listening"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', 4002))
                return {
                    'port_listening': result == 0,
                    'port': 4002,
                    'host': '127.0.0.1'
                }
        except Exception as e:
            return {'port_listening': False, 'error': str(e)}

    def check_api_health(self) -> Dict:
        """Check if API is actually authenticated and working"""
        try:
            ib = IB()
            ib.connect('127.0.0.1', 4002, clientId=999, timeout=10)

            # Test actual API functionality
            server_time = ib.reqCurrentTime()
            accounts = ib.managedAccounts()

            ib.disconnect()

            return {
                'api_connected': True,
                'authenticated': len(accounts) > 0,
                'accounts': accounts,
                'server_time': server_time,
                'test_time': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'api_connected': False,
                'authenticated': False,
                'error': str(e),
                'test_time': datetime.now().isoformat()
            }

    def get_system_resources(self) -> Dict:
        """Get system resource usage"""
        try:
            # Memory usage
            memory_result = subprocess.run(['free', '-h'], capture_output=True, text=True)

            # IB Gateway memory usage
            try:
                memory_result = subprocess.run(
                    ['ps', '-o', 'pid,rss,vsz,comm', '-p', ','.join(self.check_process_health()['pids'])],
                    capture_output=True, text=True
                )
                ib_memory = memory_result.stdout
            except:
                ib_memory = "N/A"

            return {
                'memory_info': memory_result.stdout,
                'ib_gateway_memory': ib_memory,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def check_last_successful_connection(self) -> Dict:
        """Check when the last successful API connection was"""
        try:
            status_data = self.load_status()
            if status_data and 'last_successful_connection' in status_data:
                last_success = datetime.fromisoformat(status_data['last_successful_connection'])
                time_since_success = datetime.now() - last_success

                return {
                    'last_successful_connection': status_data['last_successful_connection'],
                    'hours_since_success': time_since_success.total_seconds() / 3600,
                    'needs_authentication': time_since_success > timedelta(hours=20)  # Safety margin
                }
            else:
                return {
                    'last_successful_connection': None,
                    'hours_since_success': float('inf'),
                    'needs_authentication': True
                }
        except Exception as e:
            return {'error': str(e), 'needs_authentication': True}

    def send_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Send alert to various channels"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }

        # Log the alert
        self.logger.warning(f"ALERT: {alert_type} - {message}")

        # Save to alerts file
        try:
            alerts = self.load_alerts()
            alerts.append(alert)

            # Keep only last 100 alerts
            alerts = alerts[-100:]

            with open(self.alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save alert: {e}")

        # Here you could add email, SMS, Slack, etc.
        # For now, just create a simple alert file
        alert_file = f'{self.log_dir}/current_alert.txt'
        with open(alert_file, 'w') as f:
            f.write(f"{alert['timestamp']} - {severity.upper()}: {message}\n")

    def load_status(self) -> Optional[Dict]:
        """Load previous status"""
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except:
            return None

    def load_alerts(self) -> List[Dict]:
        """Load previous alerts"""
        try:
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def save_status(self, status: Dict):
        """Save current status"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save status: {e}")

    def comprehensive_health_check(self) -> Dict:
        """Perform comprehensive health check"""
        self.logger.info("Starting comprehensive IB Gateway health check...")

        status = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

        # Individual checks
        status['checks']['process'] = self.check_process_health()
        status['checks']['port'] = self.check_port_health()
        status['checks']['api'] = self.check_api_health()
        status['checks']['system'] = self.get_system_resources()
        status['checks']['connection_history'] = self.check_last_successful_connection()

        # Overall status determination
        process_ok = status['checks']['process']['process_running']
        port_ok = status['checks']['port']['port_listening']
        api_ok = status['checks']['api']['api_connected']
        auth_ok = status['checks']['api']['authenticated']

        status['overall_status'] = 'healthy' if (process_ok and port_ok and api_ok and auth_ok) else 'unhealthy'
        status['issues'] = []

        # Identify specific issues
        if not process_ok:
            status['issues'].append('IB Gateway process not running')
            self.send_alert('process_down', 'IB Gateway process is not running', 'critical')

        if not port_ok:
            status['issues'].append('Port 4002 not listening')
            self.send_alert('port_down', 'IB Gateway port 4002 is not accessible', 'critical')

        if not api_ok:
            status['issues'].append('API connection failed')
            self.send_alert('api_down', 'IB Gateway API is not responding', 'critical')

        if process_ok and port_ok and api_ok and not auth_ok:
            status['issues'].append('API requires authentication')
            self.send_alert('auth_required', 'IB Gateway requires manual authentication', 'warning')

        # Update last successful connection
        if api_ok and auth_ok:
            status['last_successful_connection'] = datetime.now().isoformat()

        # Save status
        self.save_status(status)

        self.logger.info(f"Health check complete: {status['overall_status']}")
        return status

    def generate_status_report(self) -> str:
        """Generate human-readable status report"""
        status = self.load_status()
        if not status:
            return "No status data available"

        report = []
        report.append("=" * 60)
        report.append("IB GATEWAY SERVER-SIDE STATUS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Overall Status: {status.get('overall_status', 'unknown').upper()}")
        report.append("")

        # Process status
        proc = status.get('checks', {}).get('process', {})
        if proc.get('process_running'):
            report.append(f"✅ Process: Running (PIDs: {', '.join(proc.get('pids', []))})")
        else:
            report.append("❌ Process: Not running")

        # Port status
        port = status.get('checks', {}).get('port', {})
        if port.get('port_listening'):
            report.append("✅ Port 4002: Listening")
        else:
            report.append("❌ Port 4002: Not accessible")

        # API status
        api = status.get('checks', {}).get('api', {})
        if api.get('api_connected') and api.get('authenticated'):
            report.append("✅ API: Authenticated and functional")
            if api.get('accounts'):
                report.append(f"   Accounts: {', '.join(api['accounts'])}")
        else:
            report.append("❌ API: Not ready")
            if 'error' in api:
                report.append(f"   Error: {api['error']}")

        # Connection history
        conn = status.get('checks', {}).get('connection_history', {})
        if conn.get('last_successful_connection'):
            last_conn = datetime.fromisoformat(conn['last_successful_connection'])
            hours_since = conn.get('hours_since_success', 0)
            report.append(f"Last Successful Connection: {last_conn.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Hours Since Success: {hours_since:.1f}")

            if conn.get('needs_authentication'):
                report.append("⚠️ Authentication likely required")

        # Recent alerts
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r') as f:
                    alerts = json.load(f)

                if alerts:
                    report.append("")
                    report.append("Recent Alerts:")
                    for alert in alerts[-5:]:  # Last 5 alerts
                        timestamp = datetime.fromisoformat(alert['timestamp'])
                        severity = alert.get('severity', 'info').upper()
                        message = alert['message']
                        report.append(f"  {timestamp.strftime('%H:%M')} [{severity}] {message}")
            except:
                pass

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)

if __name__ == "__main__":
    import sys

    monitor = IBServerMonitor()

    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            print(monitor.generate_status_report())
        elif sys.argv[1] == "check":
            status = monitor.comprehensive_health_check()
            print(json.dumps(status, indent=2))
        elif sys.argv[1] == "monitor":
            # Continuous monitoring mode
            while True:
                monitor.comprehensive_health_check()
                time.sleep(300)  # Check every 5 minutes
        else:
            print("Usage: server_monitor.py [status|check|monitor]")
    else:
        # Default: perform one comprehensive check
        status = monitor.comprehensive_health_check()
        print(json.dumps(status, indent=2))
EOF

    chmod +x /home/davidsanker/platform/bin/server_monitor.py
    log "Server monitor created"
}

# Create server-side trading bot with smart reconnection
create_smart_trading_bot() {
    log "Creating smart trading bot with server-side logic..."

    cat > /home/davidsanker/platform/bin/smart_trading_bot.py << 'EOF'
#!/usr/bin/env python3
"""
Smart Trading Bot with Server-Side Reconnection Logic
No GUI automation - handles authentication gracefully
"""

import os
import time
import logging
import signal
import json
from datetime import datetime, timedelta
from ib_insync import IB, Stock, Forex, util
from server_monitor import IBServerMonitor

class SmartTradingBot:
    def __init__(self):
        self.monitor = IBServerMonitor()
        self.ib = IB()
        self.connection_attempts = 0
        self.max_attempts = 10
        self.base_backoff = 30  # seconds
        self.max_backoff = 1800  # 30 minutes

        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/home/davidsanker/platform/logs/server-only/trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        self.running = True

    def handle_shutdown(self, signum, frame):
        self.logger.info("Shutdown signal received - stopping gracefully...")
        self.running = False
        if self.ib.isConnected():
            self.ib.disconnect()

    def smart_connect(self) -> bool:
        """Smart connection with exponential backoff and authentication awareness"""
        self.connection_attempts += 1

        if self.connection_attempts > self.max_attempts:
            self.logger.error(f"Max connection attempts ({self.max_attempts}) exceeded")
            return False

        # Calculate backoff with exponential growth
        backoff = min(self.base_backoff * (2 ** (self.connection_attempts - 1)), self.max_backoff)

        if self.connection_attempts > 1:
            self.logger.info(f"Connection attempt {self.connection_attempts}/{self.max_attempts} - waiting {backoff}s")
            time.sleep(backoff)

        try:
            # Check if Gateway needs authentication
            status = self.monitor.comprehensive_health_check()

            if not status['checks']['process']['process_running']:
                self.logger.warning("IB Gateway process not running - cannot connect")
                return False

            if not status['checks']['port']['port_listening']:
                self.logger.warning("Port 4002 not available - Gateway may be starting")
                return False

            # Attempt connection
            self.logger.info(f"Attempting IB connection (attempt {self.connection_attempts})")
            self.ib.connect('127.0.0.1', 4002, clientId=100, timeout=15)

            # Test if actually authenticated
            accounts = self.ib.managedAccounts()
            if not accounts:
                self.logger.warning("Connected but no accounts - authentication may be required")
                self.ib.disconnect()
                return False

            self.logger.info(f"✅ Successfully connected to IB. Account: {accounts[0]}")

            # Reset connection attempts on success
            self.connection_attempts = 0
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            if self.ib.isConnected():
                self.ib.disconnect()
            return False

    def wait_for_gateway_ready(self, max_wait_minutes: int = 30) -> bool:
        """Wait for IB Gateway to be ready for connections"""
        self.logger.info(f"Waiting for IB Gateway to be ready (max {max_wait_minutes} minutes)...")

        start_time = datetime.now()
        while datetime.now() - start_time < timedelta(minutes=max_wait_minutes):
            status = self.monitor.comprehensive_health_check()

            if status['overall_status'] == 'healthy':
                self.logger.info("IB Gateway is ready")
                return True

            if status['checks']['process']['process_running'] and status['checks']['port']['port_listening']:
                # Gateway is running but may need auth - try connecting
                if self.smart_connect():
                    return True

            self.logger.info("Gateway not ready yet, waiting 30 seconds...")
            time.sleep(30)

        self.logger.error("Gateway not ready after maximum wait time")
        return False

    def graceful_disconnect_handler(self):
        """Handle IB disconnects gracefully"""
        self.logger.warning("IB connection lost - entering reconnection strategy")

        # Disconnect properly
        if self.ib.isConnected():
            try:
                self.ib.disconnect()
            except:
                pass

        # Wait a bit before reconnection attempts
        time.sleep(60)

        # Try to reconnect with smart logic
        reconnect_attempts = 0
        while self.running and reconnect_attempts < 5:
            reconnect_attempts += 1
            self.logger.info(f"Reconnection attempt {reconnect_attempts}/5")

            # First, check if Gateway is healthy
            status = self.monitor.comprehensive_health_check()

            if status['overall_status'] == 'healthy':
                # Gateway is healthy, try to reconnect
                if self.smart_connect():
                    self.logger.info("✅ Successfully reconnected to IB")
                    return
            else:
                self.logger.warning(f"Gateway status: {status['overall_status']}")
                if status['issues']:
                    for issue in status['issues']:
                        self.logger.warning(f"Issue: {issue}")

            # Wait before next attempt
            time.sleep(300)  # 5 minutes

        # If we reach here, reconnection failed
        self.logger.error("Failed to reconnect after multiple attempts")
        self.monitor.send_alert('reconnection_failed',
                               'Trading bot failed to reconnect to IB Gateway after multiple attempts',
                               'critical')

    def run(self):
        """Main trading bot loop"""
        self.logger.info("Starting Smart Trading Bot...")

        # Set up event handlers
        self.ib.disconnectedEvent += self.graceful_disconnect_handler
        self.ib.errorEvent += self._on_error

        # Initial connection
        if not self.wait_for_gateway_ready():
            self.logger.error("Cannot start - IB Gateway not ready")
            return

        if not self.smart_connect():
            self.logger.error("Cannot start - failed to connect to IB Gateway")
            return

        # Main trading loop
        self.logger.info("Entering main trading loop...")
        last_heartbeat = datetime.now()

        while self.running:
            try:
                # Heartbeat check every 5 minutes
                if datetime.now() - last_heartbeat > timedelta(minutes=5):
                    self.heartbeat_check()
                    last_heartbeat = datetime.now()

                # Your trading logic here
                self.trading_logic()

                # Sleep to prevent busy loop
                time.sleep(10)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(30)  # Prevent rapid error loops

        # Cleanup
        self.logger.info("Shutting down trading bot...")
        if self.ib.isConnected():
            self.ib.disconnect()

    def heartbeat_check(self):
        """Periodic health check"""
        try:
            # Simple API call to verify connection
            self.ib.reqCurrentTime()
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {e}")

    def _on_error(self, reqId, errorCode, errorString, contract):
        """Handle IB errors"""
        self.logger.error(f"IB Error: ID={reqId}, Code={errorCode}, Message={errorString}")

        # Certain errors indicate authentication issues
        if errorCode in [502, 504, 509]:  # Common authentication/connection errors
            self.monitor.send_alert('ib_auth_error',
                                   f"IB Gateway authentication error: {errorString}",
                                   'warning')

    def trading_logic(self):
        """Placeholder for your trading strategy"""
        # Add your trading logic here
        # This is where you would implement your actual trading strategies
        pass

if __name__ == "__main__":
    bot = SmartTradingBot()
    bot.run()
EOF

    chmod +x /home/davidsanker/platform/bin/smart_trading_bot.py
    log "Smart trading bot created"
}

# Setup server-side monitoring schedule
setup_server_monitoring() {
    log "Setting up server-side monitoring schedule..."

    # Create cron entries for monitoring
    (crontab -l 2>/dev/null; echo "# Server-Side IB Gateway Monitoring") | crontab -
    (crontab -l 2>/dev/null; echo "*/10 * * * * /home/davidsanker/platform/bin/server_monitor.py check") | crontab -
    (crontab -l 2>/dev/null; echo "0 */6 * * * /home/davidsanker/platform/bin/server_monitor.py status >> /home/davidsanker/platform/logs/server-only/daily_status.log") | crontab -

    log "Server monitoring schedule configured"
}

# Main implementation
main() {
    log "=========================================="
    log "SERVER-SIDE ONLY SOLUTION IMPLEMENTATION"
    log "=========================================="

    create_server_monitor
    create_smart_trading_bot
    setup_server_monitoring

    log "✅ Server-side solution implemented"
    log ""
    log "📋 Components Created:"
    log "1. server_monitor.py - Comprehensive monitoring system"
    log "2. smart_trading_bot.py - Trading bot with smart reconnection"
    log "3. Automated monitoring schedule"
    log ""
    log "🚀 Quick Start:"
    log "1. Start monitoring: python3 /home/davidsanker/platform/bin/server_monitor.py monitor"
    log "2. Start trading bot: python3 /home/davidsanker/platform/bin/smart_trading_bot.py"
    log "3. Check status: python3 /home/davidsanker/platform/bin/server_monitor.py status"
    log ""
    log "📊 Monitoring Files:"
    log "- Status: /home/davidsanker/platform/logs/server-only/status.json"
    log "- Alerts: /home/davidsanker/platform/logs/server-only/alerts.json"
    log "- Current Alert: /home/davidsanker/platform/logs/server-only/current_alert.txt"
    log ""
    log "⚠️ Important Notes:"
    log "- This solution requires daily manual authentication"
    log "- Monitor will alert when authentication is needed"
    log "- Trading bot will handle disconnections gracefully"
    log "- No GUI automation - purely server-side monitoring"
}

# Run implementation
main