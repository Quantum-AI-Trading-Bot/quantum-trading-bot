#!/usr/bin/env python3
"""
Comprehensive IB Gateway Connection Health Monitor
Diagnoses disconnection issues and provides detailed logging
"""

import asyncio
import time
import logging
import subprocess
import json
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/davidsanker/logs/connection_health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IBGatewayHealthMonitor:
    """Comprehensive health monitoring for IB Gateway"""

    def __init__(self):
        self.monitoring_active = False
        self.monitor_interval = 30  # seconds
        self.api_port = 4002
        self.gateway_process_name = "ibgateway"

        # Connection history
        self.connection_history = []
        self.disconnection_events = []
        self.health_metrics = {
            'total_checks': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_success_time': None,
            'last_failure_time': None,
            'longest_streak': 0,
            'current_streak': 0,
            'avg_response_time': 0,
            'gateway_restarts': 0
        }

        # Previous states for comparison
        self.last_gateway_pid = None
        self.last_port_status = False
        self.last_connection_time = None

    def check_ib_gateway_process(self) -> Dict:
        """Check IB Gateway process health"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', self.gateway_process_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                processes = []

                for pid in pids:
                    if pid.strip():
                        # Get detailed process info
                        try:
                            proc_result = subprocess.run(
                                ['ps', '-p', pid.strip(), '-o', 'etime,pid,pcpu,pmem,cmd'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if proc_result.returncode == 0:
                                processes.append(proc_result.stdout.strip())
                        except:
                            processes.append(f"PID: {pid.strip()}")

                return {
                    'status': 'running',
                    'count': len(pids),
                    'pids': pids,
                    'processes': processes,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'not_running',
                    'count': 0,
                    'pids': [],
                    'processes': [],
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"❌ Process check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def check_api_port(self) -> Dict:
        """Check API port connectivity"""
        try:
            start_time = time.time()

            # Test basic TCP connection
            result = subprocess.run(
                ['nc', '-z', '127.0.0.1', str(self.api_port)],
                capture_output=True,
                timeout=10
            )

            response_time = time.time() - start_time

            if result.returncode == 0:
                # Test with telnet-like connection
                try:
                    telnet_result = subprocess.run(
                        ['timeout', '3', 'bash', '-c', f'echo "" | nc 127.0.0.1 {self.api_port}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    return {
                        'status': 'open',
                        'response_time': response_time,
                        'telnet_output': telnet_result.stdout,
                        'timestamp': datetime.now().isoformat()
                    }
                except:
                    return {
                        'status': 'open',
                        'response_time': response_time,
                        'telnet_output': '',
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                return {
                    'status': 'closed',
                    'response_time': response_time,
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }

        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'response_time': 30.0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def check_ib_insync_connection(self) -> Dict:
        """Test actual IB API connection with ib_insync"""
        try:
            start_time = time.time()

            test_script = '''
import sys
sys.path.append("/home/davidsanker/trading_bot_venv/lib/python3.11/site-packages")
from ib_insync import IB
import time

try:
    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=9999, timeout=10)
    server_time = ib.reqCurrentTime()
    ib.disconnect()
    connection_time = time.time() - start_time
    print(f"SUCCESS:{connection_time:.2f}:{server_time}")
    sys.exit(0)
except Exception as e:
    print(f"FAILED:{str(e)}")
    sys.exit(1)
'''

            result = subprocess.run(
                ['python3', '-c', test_script],
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ.copy()
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output.startswith("SUCCESS:"):
                    parts = output.split(":")
                    conn_time = float(parts[1])
                    server_time = parts[2]

                    return {
                        'status': 'connected',
                        'connection_time': conn_time,
                        'server_time': server_time,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'status': 'error',
                        'error': output,
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr or result.stdout,
                    'timestamp': datetime.now().isoformat()
                }

        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'error': 'Connection timeout after 30s',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def check_system_resources(self) -> Dict:
        """Check system resources that might affect connection"""
        try:
            # Check memory usage
            memory_result = subprocess.run(
                ['free', '-h'],
                capture_output=True,
                text=True
            )

            # Check disk space
            disk_result = subprocess.run(
                ['df', '-h', '/tmp'],
                capture_output=True,
                text=True
            )

            # Check network interfaces
            network_result = subprocess.run(
                ['netstat', '-i'],
                capture_output=True,
                text=True
            )

            return {
                'memory': memory_result.stdout,
                'disk': disk_result.stdout,
                'network': network_result.stdout,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def detect_disconnection_patterns(self) -> Dict:
        """Analyze disconnection patterns"""
        try:
            if len(self.disconnection_events) < 2:
                return {'pattern': 'insufficient_data'}

            # Analyze time patterns
            times = [datetime.fromisoformat(event['timestamp']) for event in self.disconnection_events]

            # Calculate intervals
            intervals = []
            for i in range(1, len(times)):
                interval = (times[i] - times[i-1]).total_seconds()
                intervals.append(interval)

            if not intervals:
                return {'pattern': 'no_intervals'}

            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)

            # Check for periodic patterns
            if len(intervals) >= 3:
                # Check if intervals are similar (within 20%)
                deviation = max(intervals) - min(intervals)
                if deviation / avg_interval < 0.2:
                    return {
                        'pattern': 'periodic',
                        'avg_interval': avg_interval,
                        'min_interval': min_interval,
                        'max_interval': max_interval,
                        'deviation': deviation
                    }

            return {
                'pattern': 'irregular',
                'avg_interval': avg_interval,
                'min_interval': min_interval,
                'max_interval': max_interval,
                'total_events': len(self.disconnection_events)
            }

        except Exception as e:
            return {'error': str(e)}

    def perform_health_check(self) -> Dict:
        """Perform comprehensive health check"""
        try:
            check_time = datetime.now()

            # Check all components
            process_check = self.check_ib_gateway_process()
            port_check = self.check_api_port()
            api_check = self.check_ib_insync_connection()
            system_check = self.check_system_resources()

            # Update metrics
            self.health_metrics['total_checks'] += 1

            # Determine overall status
            overall_status = 'healthy'
            issues = []

            if process_check['status'] != 'running':
                overall_status = 'critical'
                issues.append('Gateway not running')

            elif port_check['status'] != 'open':
                overall_status = 'degraded'
                issues.append('API port closed')

            elif api_check['status'] != 'connected':
                overall_status = 'critical'
                issues.append('API connection failed')

            # Record connection event
            connection_event = {
                'timestamp': check_time.isoformat(),
                'overall_status': overall_status,
                'process_status': process_check.get('status'),
                'port_status': port_check.get('status'),
                'api_status': api_check.get('status'),
                'issues': issues,
                'process_check': process_check,
                'port_check': port_check,
                'api_check': api_check,
                'system_check': system_check
            }

            # Update metrics
            if overall_status == 'healthy':
                self.health_metrics['successful_connections'] += 1
                self.health_metrics['last_success_time'] = check_time.isoformat()
                self.health_metrics['current_streak'] = 0
            else:
                self.health_metrics['failed_connections'] += 1
                self.health_metrics['last_failure_time'] = check_time.isoformat()
                self.health_metrics['current_streak'] += 1
                self.health_metrics['longest_streak'] = max(
                    self.health_metrics['longest_streak'],
                    self.health_metrics['current_streak']
                )

                # Record disconnection event
                self.disconnection_events.append(connection_event)

                # Limit history to last 100 events
                if len(self.disconnection_events) > 100:
                    self.disconnection_events = self.disconnection_events[-100:]

            # Update response time average
            if port_check.get('response_time'):
                total_response = (self.health_metrics['avg_response_time'] *
                                 (self.health_metrics['total_checks'] - 1) +
                                 port_check['response_time'])
                self.health_metrics['avg_response_time'] = total_response / self.health_metrics['total_checks']

            # Detect process restarts
            current_pids = process_check.get('pids', [])
            if self.last_gateway_pid and current_pids:
                if str(self.last_gateway_pid) not in current_pids:
                    self.health_metrics['gateway_restarts'] += 1
                    logger.warning(f"🔄 Gateway restart detected! Old PID: {self.last_gateway_pid}, New PIDs: {current_pids}")

            self.last_gateway_pid = current_pids[0] if current_pids else None

            return connection_event

        except Exception as e:
            error_event = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'overall_status': 'error'
            }
            logger.error(f"❌ Health check failed: {e}")
            return error_event

    def save_monitoring_data(self):
        """Save monitoring data to file"""
        try:
            data = {
                'monitoring_session': {
                    'start_time': datetime.now().isoformat(),
                    'monitoring_interval': self.monitor_interval,
                    'total_checks': self.health_metrics['total_checks']
                },
                'health_metrics': self.health_metrics,
                'recent_events': self.disconnection_events[-10:],  # Last 10 events
                'disconnection_patterns': self.detect_disconnection_patterns()
            }

            with open('/tmp/ib_gateway_monitoring_data.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"❌ Failed to save monitoring data: {e}")

    def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("🔍 Starting IB Gateway health monitoring loop...")

        while self.monitoring_active:
            try:
                # Perform health check
                health_result = self.perform_health_check()

                # Log status
                if health_result.get('overall_status') == 'healthy':
                    logger.info(f"✅ Health check passed - API: {health_result.get('api_status')}, Port: {health_result.get('port_status')}")
                elif health_result.get('overall_status') == 'degraded':
                    logger.warning(f"⚠️ Health check degraded - Issues: {health_result.get('issues')}")
                elif health_result.get('overall_status') == 'critical':
                    logger.error(f"❌ Critical health issues - Issues: {health_result.get('issues')}")
                else:
                    logger.error(f"💥 Health check error - {health_result.get('error')}")

                # Save monitoring data periodically
                if self.health_metrics['total_checks'] % 10 == 0:
                    self.save_monitoring_data()

                # Wait for next check
                time.sleep(self.monitor_interval)

            except KeyboardInterrupt:
                logger.info("⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"💥 Monitoring loop error: {e}")
                time.sleep(self.monitor_interval)

    def start_monitoring(self):
        """Start health monitoring"""
        if self.monitoring_active:
            logger.warning("⚠️ Monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("🚀 IB Gateway health monitoring started")

    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.join(timeout=10)
        logger.info("🛑 IB Gateway health monitoring stopped")

    def generate_diagnostic_report(self) -> str:
        """Generate comprehensive diagnostic report"""
        try:
            patterns = self.detect_disconnection_patterns()

            report = f"""
# 🔍 IB Gateway Connection Diagnostic Report
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Current Status
- Monitoring Active: {self.monitoring_active}
- Total Checks: {self.health_metrics['total_checks']}
- Success Rate: {(self.health_metrics['successful_connections'] / max(1, self.health_metrics['total_checks']) * 100):.1f}%
- Current Streak: {self.health_metrics['current_streak']} consecutive failures
- Longest Streak: {self.health_metrics['longest_streak']} consecutive failures

## 📈 Connection Metrics
- Successful Connections: {self.health_metrics['successful_connections']}
- Failed Connections: {self.health_metrics['failed_connections']}
- Gateway Restarts: {self.health_metrics['gateway_restarts']}
- Average Response Time: {self.health_metrics['avg_response_time']:.3f}s
- Last Success: {self.health_metrics['last_success_time'] or 'Never'}
- Last Failure: {self.health_metrics['last_failure_time'] or 'Never'}

## 🔍 Disconnection Analysis
- Pattern: {patterns.get('pattern', 'unknown')}
- Total Events: {len(self.disconnection_events)}
- Recent Events (Last 5): {len(self.disconnection_events[-5:])}

## 💡 Recommendations
"""

            # Add specific recommendations based on analysis
            if self.health_metrics['failed_connections'] > self.health_metrics['successful_connections']:
                report += "❌ HIGH FAILURE RATE detected\n"
                report += "- Consider checking IB Gateway stability\n"
                report += "- Verify network connectivity\n"
                report += "- Check for memory leaks\n"
            elif self.health_metrics['gateway_restarts'] > 5:
                report += "🔄 FREQUENT GATEWAY RESTARTS\n"
                report += "- Check for crash logs\n"
                report += "- Monitor memory usage\n"
                report += "- Verify Java heap size\n"

            if patterns.get('pattern') == 'periodic':
                report += f"⏰ PERIODIC DISCONNECTIONS detected\n"
                report += f"- Average interval: {patterns.get('avg_interval', 0):.0f} seconds\n"
                report += "- Check for scheduled maintenance\n"
                report += "- Review automated scripts\n"

            # Add recent events
            if self.disconnection_events:
                report += "\n## 📋 Recent Disconnection Events\n"
                for event in self.disconnection_events[-5:]:
                    report += f"- {event['timestamp']}: {event.get('overall_status', 'unknown')} - {event.get('issues', [])}\n"

            return report

        except Exception as e:
            return f"❌ Failed to generate report: {e}"

def main():
    """Main entry point"""
    monitor = IBGatewayHealthMonitor()

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"📡 Received signal {signum}, stopping monitor...")
        monitor.stop_monitoring()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("🚀 Starting IB Gateway Connection Health Monitor...")

        # Start monitoring
        monitor.start_monitoring()

        # Keep running
        while monitor.monitoring_active:
            time.sleep(1)

        # Generate final report
        report = monitor.generate_diagnostic_report()
        print("\n" + "="*60)
        print(report)

        # Save report
        with open('/tmp/ib_gateway_diagnostic_report.txt', 'w') as f:
            f.write(report)

        print(f"\n📄 Diagnostic report saved to: /tmp/ib_gateway_diagnostic_report.txt")
        print(f"📊 Monitoring data saved to: /tmp/ib_gateway_monitoring_data.json")

        return True

    except KeyboardInterrupt:
        logger.info("⏹️ Monitor stopped by user")
        return True
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)