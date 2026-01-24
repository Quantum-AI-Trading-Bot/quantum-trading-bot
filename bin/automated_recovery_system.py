#!/usr/bin/env python3
"""
Automated Recovery System for Trading Bot Failures
Detects failures and executes recovery procedures automatically
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
import psutil

# Add platform to path
sys.path.append('/home/davidsanker/platform')

class AutomatedRecoverySystem:
    """Automated recovery system for trading bot failures"""

    def __init__(self):
        self.logger = self.setup_logging()
        self.recovery_history = []
        self.last_recovery_actions = {}

    def setup_logging(self):
        """Setup recovery logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - RECOVERY - %(message)s',
            handlers=[
                logging.FileHandler('/home/davidsanker/platform/logs/recovery_system.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def check_ib_gateway_failure(self) -> Optional[str]:
        """Check for IB Gateway failure modes"""
        try:
            # Check if process is running
            result = subprocess.run(['pgrep', '-f', 'java.*ibgateway'],
                                  capture_output=True, text=True)

            if result.returncode != 0:
                return "IB Gateway process not found"

            pid = result.stdout.strip()

            # Check for high memory usage
            try:
                process = psutil.Process(int(pid))
                memory_mb = process.memory_info().rss / 1024 / 1024

                if memory_mb > 1800:
                    return f"High memory usage: {memory_mb:.1f}MB"

                # Check if API is responsive
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('127.0.0.1', 4002))
                sock.close()

                if result != 0:
                    return "API not responding on port 4002"

            except psutil.NoSuchProcess:
                return "Process disappeared during check"

            return None

        except Exception as e:
            return f"Health check error: {str(e)}"

    def check_trading_bot_failure(self) -> Optional[str]:
        """Check for trading bot failure modes"""
        try:
            # Check if process is running
            result = subprocess.run(['pgrep', '-f', 'python.*trading'],
                                  capture_output=True, text=True)

            if result.returncode != 0:
                return "No trading bot process found"

            # Check recent logs for errors
            log_files = ['/tmp/active_trading_final.log', '/tmp/trading_bot_output.log']

            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        # Check last 10 lines for critical errors
                        with open(log_file, 'r') as f:
                            lines = f.readlines()[-10:]

                        for line in lines:
                            if 'TimeoutError' in line:
                                return "Connection timeout errors detected"
                            if 'clientId already in use' in line:
                                return "Client ID conflict detected"
                            if 'Connection refused' in line:
                                return "Connection refused errors detected"

                    except Exception:
                        continue

            return None

        except Exception as e:
            return f"Health check error: {str(e)}"

    def restart_ib_gateway(self) -> bool:
        """Restart IB Gateway with proper cleanup"""
        try:
            self.logger.info("Starting IB Gateway recovery...")

            # Kill existing processes
            self.logger.info("Killing existing IB Gateway processes...")
            subprocess.run(['pkill', '-f', 'java.*ibgateway'], capture_output=True)
            time.sleep(5)

            # Verify processes are killed
            result = subprocess.run(['pgrep', '-f', 'java.*ibgateway'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.warning("Some processes still running, force killing...")
                subprocess.run(['pkill', '-9', '-f', 'java.*ibgateway'], capture_output=True)
                time.sleep(3)

            # Start IB Gateway via IBC
            self.logger.info("Starting IB Gateway via IBC...")
            subprocess.run([
                'bash', '-c',
                'export DISPLAY=:1 && /home/davidsanker/IBC/gatewaystart.sh'
            ], capture_output=True, timeout=30)

            # Wait for startup
            time.sleep(20)

            # Verify it's running
            result = subprocess.run(['pgrep', '-f', 'java.*ibgateway'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"IB Gateway restarted successfully (PID: {result.stdout.strip()})")
                return True
            else:
                self.logger.error("IB Gateway failed to restart")
                return False

        except Exception as e:
            self.logger.error(f"IB Gateway recovery failed: {e}")
            return False

    def restart_trading_bot(self) -> bool:
        """Restart trading bot with new client ID"""
        try:
            self.logger.info("Starting trading bot recovery...")

            # Kill existing trading processes
            self.logger.info("Killing existing trading bot processes...")
            subprocess.run(['pkill', '-f', 'python.*trading'], capture_output=True)
            subprocess.run(['pkill', '-f', 'trading_bot'], capture_output=True)
            time.sleep(3)

            # Generate new client ID to avoid conflicts
            import random
            new_client_id = random.randint(8000, 9999)

            # Start trading bot with new client ID
            self.logger.info(f"Starting trading bot with client ID {new_client_id}...")

            # Create updated trading bot script
            bot_script = f"""#!/usr/bin/env python3
import sys
sys.path.append('/home/davidsanker/platform')
from ib_insync import IB, util
import time

util.startLoop()
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId={new_client_id}, timeout=15)
    print(f'✅ Trading bot started with Client ID: {{new_client_id}}')
    print('📊 Account:', ib.managedAccounts()[0])
    print('🚀 Trading bot is ACTIVE and monitoring...')

    # Keep running
    ib.run()
except Exception as e:
    print(f'❌ Trading bot error: {{e}}')
    sys.exit(1)
"""

            # Write and execute
            with open('/tmp/recovery_trading_bot.py', 'w') as f:
                f.write(bot_script)

            subprocess.Popen([
                'bash', '-c',
                f'source ~/venv/bin/activate && python3 /tmp/recovery_trading_bot.py > /tmp/recovery_trading_output.log 2>&1 &'
            ])

            # Wait for startup
            time.sleep(10)

            # Check if it's running
            result = subprocess.run(['pgrep', '-f', 'recovery_trading_bot'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Trading bot restarted successfully (PID: {result.stdout.strip()})")
                return True
            else:
                self.logger.error("Trading bot failed to restart")
                return False

        except Exception as e:
            self.logger.error(f"Trading bot recovery failed: {e}")
            return False

    def handle_authentication_failure(self) -> bool:
        """Handle IB Gateway authentication failure"""
        try:
            self.logger.info("Handling authentication failure...")

            # Use automated GUI authentication
            self.logger.info("Starting automated GUI authentication...")
            result = subprocess.run([
                '/home/davidsanker/platform/bin/auto_login_gui.sh'
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                self.logger.info("Automated authentication completed")
                return True
            else:
                self.logger.warning("Automated authentication failed, manual intervention required")
                return False

        except Exception as e:
            self.logger.error(f"Authentication recovery failed: {e}")
            return False

    def handle_memory_exhaustion(self, process_type: str) -> bool:
        """Handle memory exhaustion issues"""
        try:
            self.logger.info(f"Handling memory exhaustion for {process_type}...")

            if process_type == "ib_gateway":
                # Restart IB Gateway
                return self.restart_ib_gateway()
            elif process_type == "trading_bot":
                # Restart trading bot
                return self.restart_trading_bot()

            return False

        except Exception as e:
            self.logger.error(f"Memory exhaustion recovery failed: {e}")
            return False

    def execute_recovery_action(self, failure_type: str, details: str) -> bool:
        """Execute appropriate recovery action based on failure type"""
        try:
            self.logger.info(f"Executing recovery for {failure_type}: {details}")

            # Check cooldown period (avoid rapid restarts)
            action_key = f"{failure_type}_{details}"
            current_time = datetime.now()

            if action_key in self.last_recovery_actions:
                time_since_last = current_time - self.last_recovery_actions[action_key]
                if time_since_last < timedelta(minutes=5):
                    self.logger.warning(f"Recovery action in cooldown period ({time_since_last} ago)")
                    return False

            # Execute recovery based on failure type
            success = False

            if "IB Gateway" in failure_type:
                if "process not found" in details:
                    success = self.restart_ib_gateway()
                elif "API not responding" in details:
                    success = self.restart_ib_gateway()
                elif "High memory usage" in details:
                    success = self.handle_memory_exhaustion("ib_gateway")
                elif "authentication" in details.lower():
                    success = self.handle_authentication_failure()

            elif "trading bot" in failure_type:
                if "process not found" in details:
                    success = self.restart_trading_bot()
                elif "timeout" in details.lower():
                    success = self.restart_trading_bot()
                elif "client id" in details.lower():
                    success = self.restart_trading_bot()
                elif "High memory usage" in details:
                    success = self.handle_memory_exhaustion("trading_bot")

            # Record recovery attempt
            if success:
                self.last_recovery_actions[action_key] = current_time
                self.recovery_history.append({
                    'timestamp': current_time.isoformat(),
                    'failure_type': failure_type,
                    'details': details,
                    'success': True
                })
                self.logger.info(f"Recovery successful for {failure_type}")
            else:
                self.recovery_history.append({
                    'timestamp': current_time.isoformat(),
                    'failure_type': failure_type,
                    'details': details,
                    'success': False
                })
                self.logger.error(f"Recovery failed for {failure_type}")

            # Save recovery history
            with open('/home/davidsanker/platform/data/recovery_history.json', 'w') as f:
                json.dump(self.recovery_history[-50:], f)  # Keep last 50 records

            return success

        except Exception as e:
            self.logger.error(f"Recovery action failed: {e}")
            return False

    def run_continuous_recovery(self):
        """Run continuous monitoring and recovery"""
        self.logger.info("Starting automated recovery system...")

        while True:
            try:
                # Check IB Gateway
                ib_failure = self.check_ib_gateway_failure()
                if ib_failure:
                    self.logger.warning(f"IB Gateway failure detected: {ib_failure}")
                    self.execute_recovery_action("IB Gateway", ib_failure)

                # Check trading bot
                bot_failure = self.check_trading_bot_failure()
                if bot_failure:
                    self.logger.warning(f"Trading bot failure detected: {bot_failure}")
                    self.execute_recovery_action("Trading Bot", bot_failure)

                # Check system resources
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                if cpu_percent > 95:
                    self.logger.warning(f"High CPU usage: {cpu_percent}%")
                    # Handle high CPU (could be runaway process)

                if memory.percent > 90:
                    self.logger.warning(f"High memory usage: {memory.percent}%")
                    # Handle high memory

                if disk.percent > 95:
                    self.logger.error(f"Critical disk usage: {disk.percent}%")
                    # Handle disk space (cleanup logs, etc.)

                time.sleep(30)  # Check every 30 seconds

            except KeyboardInterrupt:
                self.logger.info("Recovery system stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Recovery monitoring error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    recovery = AutomatedRecoverySystem()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        recovery.run_continuous_recovery()
    else:
        # Run one-time check
        ib_failure = recovery.check_ib_gateway_failure()
        bot_failure = recovery.check_trading_bot_failure()

        if ib_failure:
            print(f"IB Gateway Issue: {ib_failure}")
        if bot_failure:
            print(f"Trading Bot Issue: {bot_failure}")

        if not ib_failure and not bot_failure:
            print("✅ No failures detected")