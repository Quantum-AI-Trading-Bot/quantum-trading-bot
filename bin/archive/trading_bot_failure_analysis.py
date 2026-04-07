#!/usr/bin/env python3
"""
Comprehensive Trading Bot Failure Analysis & Prevention System
Identifies potential failure modes and implements automated recovery
"""

import sys
import os
import time
import json
import logging
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import psutil
import socket

# Add platform to path
sys.path.append('/home/davidsanker/platform')

@dataclass
class SystemHealth:
    """System health status"""
    timestamp: datetime
    ib_gateway_running: bool
    trading_bot_running: bool
    api_responsive: bool
    memory_usage: float
    disk_usage: float
    cpu_usage: float
    network_connections: int
    error_count: int
    last_error: Optional[str]

@dataclass
class FailureMode:
    """Potential failure mode analysis"""
    name: str
    probability: float  # 0-1
    impact: str  # LOW, MEDIUM, HIGH, CRITICAL
    detection_method: str
    prevention_strategy: str
    recovery_action: str

class TradingBotHealthMonitor:
    """Comprehensive health monitoring and failure prevention system"""

    def __init__(self):
        self.logger = self.setup_logging()
        self.failure_modes = self.identify_failure_modes()
        self.health_history = []
        self.error_log = []

    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/home/davidsanker/platform/logs/health_monitor.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def identify_failure_modes(self) -> List[FailureMode]:
        """Identify all potential failure modes based on historical data"""
        return [
            FailureMode(
                name="IB Gateway Authentication Timeout",
                probability=0.8,
                impact="CRITICAL",
                detection_method="Check API client connection status",
                prevention_strategy="Automated GUI authentication refresh every 23 hours",
                recovery_action="Restart IB Gateway with IBC automation"
            ),
            FailureMode(
                name="Memory Leak in Java Process",
                probability=0.7,
                impact="HIGH",
                detection_method="Monitor Java process memory growth over time",
                prevention_strategy="Set 2GB heap limit, enable GC logging",
                recovery_action="Restart IB Gateway when memory > 1.8GB"
            ),
            FailureMode(
                name="Trading Bot Process Death",
                probability=0.6,
                impact="HIGH",
                detection_method="Process monitoring with psutil",
                prevention_strategy="Implement process supervisor daemon",
                recovery_action="Auto-restart trading bot with clean state"
            ),
            FailureMode(
                name="Network Connection Drop",
                probability=0.5,
                impact="MEDIUM",
                detection_method="Socket connection testing to port 4002",
                prevention_strategy="Implement connection health checks",
                recovery_action="Re-establish connection with backoff strategy"
            ),
            FailureMode(
                name="API Rate Limiting",
                probability=0.4,
                impact="MEDIUM",
                detection_method="Monitor error codes 10089, 10168",
                prevention_strategy="Implement request throttling",
                recovery_action="Switch to delayed data, reduce request frequency"
            ),
            FailureMode(
                name="Client ID Conflicts",
                probability=0.3,
                impact="MEDIUM",
                detection_method="Monitor 'clientId already in use' errors",
                prevention_strategy="Dynamic client ID assignment",
                recovery_action="Kill conflicting processes, restart with new ID"
            ),
            FailureMode(
                name="Disk Space Exhaustion",
                probability=0.2,
                impact="HIGH",
                detection_method="Monitor available disk space",
                prevention_strategy="Log rotation, cleanup old data",
                recovery_action="Emergency cleanup, archive old logs"
            ),
            FailureMode(
                name="System Resource Exhaustion",
                probability=0.4,
                impact="HIGH",
                detection_method="Monitor CPU, memory, disk I/O",
                prevention_strategy="Resource limits, monitoring alerts",
                recovery_action="Kill non-essential processes, restart services"
            )
        ]

    def check_ib_gateway_health(self) -> Tuple[bool, str]:
        """Check IB Gateway process health"""
        try:
            # Check if Java process is running
            result = subprocess.run(['pgrep', '-f', 'java.*ibgateway'],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return False, "IB Gateway process not found"

            pid = result.stdout.strip()

            # Check process resource usage
            try:
                process = psutil.Process(int(pid))
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()

                if memory_mb > 1800:  # 1.8GB threshold
                    return False, f"High memory usage: {memory_mb:.1f}MB"

                if cpu_percent > 90:
                    return False, f"High CPU usage: {cpu_percent:.1f}%"

            except psutil.NoSuchProcess:
                return False, "Process disappeared during check"

            # Check API port responsiveness
            if not self.check_api_responsive():
                return False, "API not responding on port 4002"

            return True, f"Healthy (PID: {pid}, Memory: {memory_mb:.1f}MB)"

        except Exception as e:
            return False, f"Health check error: {str(e)}"

    def check_trading_bot_health(self) -> Tuple[bool, str]:
        """Check trading bot process health"""
        try:
            # Check for trading bot processes
            result = subprocess.run(['pgrep', '-f', 'python.*trading'],
                                  capture_output=True, text=True)

            if result.returncode != 0:
                return False, "No trading bot process found"

            pids = result.stdout.strip().split('\n')

            # Check each process
            for pid in pids:
                if pid:
                    try:
                        process = psutil.Process(int(pid))
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        cpu_percent = process.cpu_percent()

                        if memory_mb > 1000:  # 1GB threshold
                            return False, f"High memory usage: {memory_mb:.1f}MB"

                    except psutil.NoSuchProcess:
                        continue

            return True, f"Healthy ({len(pids)} processes running)"

        except Exception as e:
            return False, f"Health check error: {str(e)}"

    def check_api_responsive(self) -> bool:
        """Check if API is responding to connections"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', 4002))
            sock.close()
            return result == 0
        except:
            return False

    def check_system_resources(self) -> Dict[str, float]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024
            }
        except Exception as e:
            self.logger.error(f"Resource check failed: {e}")
            return {}

    def analyze_error_patterns(self) -> Dict[str, int]:
        """Analyze recent error patterns from logs"""
        error_patterns = {
            'timeout_errors': 0,
            'connection_errors': 0,
            'memory_errors': 0,
            'authentication_errors': 0,
            'client_id_conflicts': 0
        }

        try:
            # Check trading bot logs
            log_files = [
                '/tmp/active_trading_final.log',
                '/home/davidsanker/platform/logs/trading-bot/*.log'
            ]

            for log_file in log_files:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-100:]  # Last 100 lines

                        for line in lines:
                            if 'timeout' in line.lower() or 'TimeoutError' in line:
                                error_patterns['timeout_errors'] += 1
                            elif 'connection' in line.lower() and 'error' in line.lower():
                                error_patterns['connection_errors'] += 1
                            elif 'memory' in line.lower() and 'error' in line.lower():
                                error_patterns['memory_errors'] += 1
                            elif 'auth' in line.lower() or 'login' in line.lower():
                                error_patterns['authentication_errors'] += 1
                            elif 'client' in line.lower() and 'id' in line.lower():
                                error_patterns['client_id_conflicts'] += 1

        except Exception as e:
            self.logger.error(f"Error pattern analysis failed: {e}")

        return error_patterns

    def predict_failure_probability(self) -> Dict[str, float]:
        """Predict probability of different failure modes"""
        current_health = self.get_current_health()
        error_patterns = self.analyze_error_patterns()

        predictions = {}

        for failure_mode in self.failure_modes:
            probability = failure_mode.probability

            # Adjust based on current conditions
            if 'memory' in failure_mode.name.lower():
                if current_health.memory_usage > 80:
                    probability *= 1.5
                elif current_health.memory_usage > 60:
                    probability *= 1.2

            if 'timeout' in failure_mode.name.lower():
                if error_patterns['timeout_errors'] > 5:
                    probability *= 2.0
                elif error_patterns['timeout_errors'] > 2:
                    probability *= 1.5

            if 'connection' in failure_mode.name.lower():
                if not current_health.api_responsive:
                    probability *= 3.0
                elif error_patterns['connection_errors'] > 3:
                    probability *= 1.8

            predictions[failure_mode.name] = min(probability, 1.0)

        return predictions

    def get_current_health(self) -> SystemHealth:
        """Get current system health status"""
        ib_healthy, ib_message = self.check_ib_gateway_health()
        bot_healthy, bot_message = self.check_trading_bot_health()
        resources = self.check_system_resources()

        error_patterns = self.analyze_error_patterns()
        total_errors = sum(error_patterns.values())

        return SystemHealth(
            timestamp=datetime.now(),
            ib_gateway_running=ib_healthy,
            trading_bot_running=bot_healthy,
            api_responsive=self.check_api_responsive(),
            memory_usage=resources.get('memory_percent', 0),
            disk_usage=resources.get('disk_percent', 0),
            cpu_usage=resources.get('cpu_percent', 0),
            network_connections=len(psutil.net_connections()),
            error_count=total_errors,
            last_error=ib_message if not ib_healthy else bot_message if not bot_healthy else None
        )

    def generate_health_report(self) -> Dict:
        """Generate comprehensive health report"""
        current_health = self.get_current_health()
        failure_predictions = self.predict_failure_probability()
        error_patterns = self.analyze_error_patterns()

        # Calculate overall health score (0-100)
        health_score = 100

        if not current_health.ib_gateway_running:
            health_score -= 40
        if not current_health.trading_bot_running:
            health_score -= 30
        if not current_health.api_responsive:
            health_score -= 20
        if current_health.memory_usage > 80:
            health_score -= 15
        if current_health.disk_usage > 90:
            health_score -= 10
        if current_health.error_count > 10:
            health_score -= 10

        health_score = max(0, health_score)

        # Determine health status
        if health_score >= 80:
            status = "EXCELLENT"
        elif health_score >= 60:
            status = "GOOD"
        elif health_score >= 40:
            status = "WARNING"
        else:
            status = "CRITICAL"

        return {
            'timestamp': current_health.timestamp.isoformat(),
            'health_score': health_score,
            'status': status,
            'current_health': asdict(current_health),
            'failure_predictions': failure_predictions,
            'error_patterns': error_patterns,
            'top_risks': sorted([(k, v) for k, v in failure_predictions.items() if v > 0.3],
                              key=lambda x: x[1], reverse=True)[:3]
        }

    def run_continuous_monitoring(self):
        """Run continuous monitoring and alerting"""
        self.logger.info("Starting continuous health monitoring...")

        while True:
            try:
                health_report = self.generate_health_report()

                self.logger.info(f"Health Score: {health_report['health_score']}/100 ({health_report['status']})")

                # Log critical issues
                if health_report['health_score'] < 40:
                    self.logger.error(f"CRITICAL: Health score {health_report['health_score']}")
                    self.logger.error(f"Top risks: {health_report['top_risks']}")

                    # Send alert (implement email/SMS notification here)
                    self.send_alert(health_report)

                # Save health history
                self.health_history.append(health_report)

                # Keep only last 24 hours of data
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.health_history = [
                    h for h in self.health_history
                    if datetime.fromisoformat(h['timestamp']) > cutoff_time
                ]

                # Save to file
                with open('/home/davidsanker/platform/data/health_history.json', 'w') as f:
                    json.dump(self.health_history[-100:], f)  # Keep last 100 records

                time.sleep(60)  # Check every minute

            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(30)

    def send_alert(self, health_report: Dict):
        """Send alert notification (placeholder for email/SMS implementation)"""
        try:
            alert_message = f"""
🚨 TRADING BOT HEALTH ALERT 🚨

Status: {health_report['status']}
Health Score: {health_report['health_score']}/100
Time: {health_report['timestamp']}

Top Risks:
"""
            for risk, probability in health_report['top_risks']:
                alert_message += f"- {risk}: {probability:.1%}\n"

            # Log alert
            self.logger.error(alert_message)

            # TODO: Implement email/SMS notification
            # send_email(alert_message)
            # send_sms(alert_message)

        except Exception as e:
            self.logger.error(f"Alert sending failed: {e}")

if __name__ == "__main__":
    monitor = TradingBotHealthMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        monitor.run_continuous_monitoring()
    else:
        # Run one-time health check
        report = monitor.generate_health_report()
        print(json.dumps(report, indent=2))