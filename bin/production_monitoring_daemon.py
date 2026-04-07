#!/usr/bin/env python3
"""
Production-Grade Monitoring Daemon
Implements comprehensive monitoring with systemd integration
"""

import sys
import os
import time
import json
import logging
import subprocess
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import threading
import requests

# Add platform to path
sys.path.append('/home/davidsanker/platform')

@dataclass
class AlertConfig:
    """Alert configuration"""
    email_enabled: bool = True
    email_recipients: List[str] = None
    sms_enabled: bool = False
    sms_recipients: List[str] = None
    webhook_url: str = None
    alert_threshold: int = 40  # Health score threshold

class ProductionMonitoringDaemon:
    """Production-grade monitoring daemon with full alerting"""

    def __init__(self):
        self.logger = self.setup_logging()
        self.alert_config = self.load_alert_config()
        self.running = True
        self.health_monitor = None
        self.recovery_system = None
        self.metrics_history = []
        self.last_alerts = {}

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_logging(self):
        """Setup daemon logging"""
        log_dir = '/home/davidsanker/platform/logs'
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [DAEMON] - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/monitoring_daemon.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def load_alert_config(self) -> AlertConfig:
        """Load alert configuration"""
        config_file = '/home/davidsanker/platform/config/monitoring_config.json'

        default_config = AlertConfig(
            email_enabled=False,
            email_recipients=['david@sanker.at', 'miriam.sanker@gmail.com']
        )

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    return AlertConfig(**config_data)
            else:
                # Create default config
                with open(config_file, 'w') as f:
                    json.dump(default_config.__dict__, f, indent=2)
                return default_config
        except Exception as e:
            self.logger.error(f"Failed to load alert config: {e}")
            return default_config

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def send_email_alert(self, subject: str, message: str):
        """Send email alert (placeholder implementation)"""
        # EMAIL SENDING DISABLED - 2026-02-10
        self.logger.info(f"[EMAIL DISABLED] Would have sent: {subject}")
        return

        try:
            # TODO: Implement actual email sending
            self.logger.info(f"EMAIL ALERT - {subject}")
            self.logger.info(message)

            # For now, just log - implement SMTP/ses/sendgrid later
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = 'trading-bot@davidsanker.at'
            msg['To'] = ', '.join(self.alert_config.email_recipients)

            # Placeholder for email sending
            # server = smtplib.SMTP('smtp.gmail.com', 587)
            # server.send_message(msg)
            # server.quit()

        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    def send_webhook_alert(self, alert_data: Dict):
        """Send webhook alert"""
        try:
            if self.alert_config.webhook_url:
                response = requests.post(
                    self.alert_config.webhook_url,
                    json=alert_data,
                    timeout=10
                )
                self.logger.info(f"Webhook alert sent: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    def send_alert(self, alert_type: str, health_report: Dict):
        """Send comprehensive alert"""
        try:
            # Check cooldown (don't spam alerts)
            alert_key = f"{alert_type}_{health_report['status']}"
            current_time = datetime.now()

            if alert_key in self.last_alerts:
                time_since_last = current_time - self.last_alerts[alert_key]
                if time_since_last < timedelta(minutes=15):
                    return  # In cooldown

            self.last_alerts[alert_key] = current_time

            # Create alert message
            subject = f"🚨 Trading Bot Alert: {health_report['status']} - Score: {health_report['health_score']}"

            message = f"""
Trading Bot System Alert

Status: {health_report['status']}
Health Score: {health_report['health_score']}/100
Time: {health_report['timestamp']}

System Components:
- IB Gateway: {'✅ Running' if health_report['current_health']['ib_gateway_running'] else '❌ Down'}
- Trading Bot: {'✅ Running' if health_report['current_health']['trading_bot_running'] else '❌ Down'}
- API Connection: {'✅ Responsive' if health_report['current_health']['api_responsive'] else '❌ Not Responding'}

System Resources:
- CPU: {health_report['current_health']['cpu_usage']:.1f}%
- Memory: {health_report['current_health']['memory_usage']:.1f}%
- Disk: {health_report['current_health']['disk_usage']:.1f}%
- Errors: {health_report['current_health']['error_count']}

Top Risks:
"""
            for risk, probability in health_report['top_risks']:
                message += f"- {risk}: {probability:.1%}\n"

            if health_report['current_health']['last_error']:
                message += f"\nLast Error: {health_report['current_health']['last_error']}"

            # Send alerts
            if self.alert_config.email_enabled:
                self.send_email_alert(subject, message)

            # Send webhook
            webhook_data = {
                'alert_type': alert_type,
                'subject': subject,
                'message': message,
                'health_report': health_report,
                'timestamp': current_time.isoformat()
            }
            self.send_webhook_alert(webhook_data)

            self.logger.info(f"Alert sent: {alert_type} - {health_report['status']}")

        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")

    def collect_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            from trading_bot_failure_analysis import TradingBotHealthMonitor
            health_monitor = TradingBotHealthMonitor()
            health_report = health_monitor.generate_health_report()

            # Add additional metrics
            import psutil
            system_metrics = {
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time(),
                'processes': len(psutil.pids()),
                'boot_time': psutil.boot_time(),
                'network_connections': len(psutil.net_connections())
            }

            # Trading specific metrics
            trading_metrics = self.collect_trading_metrics()

            combined_metrics = {
                'health_report': health_report,
                'system_metrics': system_metrics,
                'trading_metrics': trading_metrics
            }

            self.metrics_history.append(combined_metrics)

            # Keep only last 1000 records
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            # Save metrics
            self.save_metrics()

            return combined_metrics

        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            return None

    def collect_trading_metrics(self):
        """Collect trading-specific metrics"""
        try:
            trading_metrics = {
                'active_orders': 0,
                'open_positions': 0,
                'daily_trades': 0,
                'daily_pnl': 0.0,
                'last_trade_time': None
            }

            # Try to get trading metrics from IB
            try:
                from ib_insync import IB, util
                util.startLoop()
                ib = IB()
                ib.connect('127.0.0.1', 4002, clientId=9999, timeout=5)

                trading_metrics['active_orders'] = len(ib.openOrders())
                trading_metrics['open_positions'] = len(ib.positions())

                # Get recent trades
                fills = ib.fills()
                today = datetime.now().date()
                daily_fills = [fill for fill in fills
                             if fill.time.date() == today]

                trading_metrics['daily_trades'] = len(daily_fills)

                if daily_fills:
                    last_fill = daily_fills[-1]
                    trading_metrics['last_trade_time'] = last_fill.time.isoformat()
                    # Calculate daily PnL
                    trading_metrics['daily_pnl'] = sum(fill.realizedPNL or 0 for fill in daily_fills)

                ib.disconnect()

            except Exception as e:
                # Can't connect to IB, use default values
                pass

            return trading_metrics

        except Exception as e:
            self.logger.error(f"Failed to collect trading metrics: {e}")
            return {}

    def save_metrics(self):
        """Save metrics to file"""
        try:
            os.makedirs('/home/davidsanker/platform/data', exist_ok=True)
            with open('/home/davidsanker/platform/data/metrics_history.json', 'w') as f:
                json.dump(self.metrics_history[-100:], f)  # Keep last 100 records
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def create_status_dashboard_data(self):
        """Create data for status dashboard"""
        try:
            if not self.metrics_history:
                return {}

            latest_metrics = self.metrics_history[-1]

            # Calculate trends
            if len(self.metrics_history) >= 2:
                previous_metrics = self.metrics_history[-2]
                health_trend = latest_metrics['health_report']['health_score'] - previous_metrics['health_report']['health_score']
            else:
                health_trend = 0

            dashboard_data = {
                'timestamp': latest_metrics['health_report']['timestamp'],
                'status': latest_metrics['health_report']['status'],
                'health_score': latest_metrics['health_report']['health_score'],
                'health_trend': health_trend,
                'components': {
                    'ib_gateway': latest_metrics['health_report']['current_health']['ib_gateway_running'],
                    'trading_bot': latest_metrics['health_report']['current_health']['trading_bot_running'],
                    'api_connection': latest_metrics['health_report']['current_health']['api_responsive']
                },
                'resources': {
                    'cpu': latest_metrics['health_report']['current_health']['cpu_usage'],
                    'memory': latest_metrics['health_report']['current_health']['memory_usage'],
                    'disk': latest_metrics['health_report']['current_health']['disk_usage']
                },
                'trading': latest_metrics.get('trading_metrics', {}),
                'top_risks': latest_metrics['health_report']['top_risks'],
                'uptime': latest_metrics['system_metrics']['uptime']
            }

            # Save dashboard data
            with open('/home/davidsanker/platform/data/status_dashboard.json', 'w') as f:
                json.dump(dashboard_data, f, indent=2)

            return dashboard_data

        except Exception as e:
            self.logger.error(f"Failed to create dashboard data: {e}")
            return {}

    def run_daemon(self):
        """Main daemon loop"""
        self.logger.info("Starting production monitoring daemon...")

        while self.running:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                if metrics:
                    # Create dashboard data
                    dashboard_data = self.create_status_dashboard_data()

                    # Check for alerts
                    health_score = metrics['health_report']['health_score']
                    status = metrics['health_report']['status']

                    if health_score < self.alert_config.alert_threshold:
                        self.send_alert('HEALTH_CRITICAL', metrics['health_report'])
                    elif status == 'WARNING':
                        self.send_alert('HEALTH_WARNING', metrics['health_report'])

                    # Log status
                    self.logger.info(f"Health Score: {health_score}/100 ({status})")

                    if metrics['trading_metrics']:
                        self.logger.info(f"Trading: {metrics['trading_metrics'].get('daily_trades', 0)} trades today")

                # Sleep before next iteration
                time.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Daemon error: {e}")
                time.sleep(30)  # Shorter sleep on error

        self.logger.info("Production monitoring daemon stopped")

def create_systemd_service():
    """Create systemd service for the monitoring daemon"""
    service_content = """[Unit]
Description=Trading Bot Production Monitoring Daemon
After=network.target

[Service]
Type=simple
User=davidsanker
WorkingDirectory=/home/davidsanker
Environment=DISPLAY=:1
ExecStart=/home/davidsanker/venv/bin/python3 /home/davidsanker/platform/bin/production_monitoring_daemon.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    try:
        with open('/etc/systemd/system/trading-monitor.service', 'w') as f:
            f.write(service_content)

        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', 'enable', 'trading-monitor.service'], check=True)

        print("✅ Systemd service created: trading-monitor.service")
        print("To start: sudo systemctl start trading-monitor")
        print("To check status: sudo systemctl status trading-monitor")

    except Exception as e:
        print(f"Failed to create systemd service: {e}")
        print("You need sudo privileges to create the service")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-service":
        create_systemd_service()
    else:
        daemon = ProductionMonitoringDaemon()
        daemon.run_daemon()