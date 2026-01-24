#!/usr/bin/env python3
"""
Simplified IB Gateway Auto-Start with IBC Integration
Focuses on what we can control: IBC configuration and monitoring
"""

import subprocess
import time
import logging
import os
import sys
from typing import Optional

class IBGatewayAutoStart:
    """Simplified IB Gateway auto-start using IBC"""

    def __init__(self):
        self.ibc_config = "/home/davidsanker/IBC/config.ini"
        self.ibc_jar = "/home/davidsanker/IBC/IBC.jar"
        self.port = 4002
        self.max_wait_time = 300  # 5 minutes

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def kill_existing_processes(self) -> bool:
        """Kill existing IB Gateway and IBC processes"""
        try:
            self.logger.info("🛑 Killing existing processes...")

            processes_to_kill = [
                "java.*ibgateway",
                "java.*IBC",
                "ibgateway",
                "IBC.jar"
            ]

            for process in processes_to_kill:
                subprocess.run(["pkill", "-f", process], check=False)

            time.sleep(3)
            self.logger.info("✅ Process cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Process cleanup failed: {e}")
            return False

    def enhance_ibc_config(self) -> bool:
        """Enhance IBC configuration for better automation"""
        try:
            self.logger.info("⚙️ Enhancing IBC configuration...")

            # Read current config
            with open(self.ibc_config, 'r') as f:
                config_content = f.read()

            # Enhanced configuration
            enhanced_config = config_content.replace(
                "SecondFactorAuthenticationTimeout=180",
                "SecondFactorAuthenticationTimeout=300"
            ).replace(
                "ReloginAfterSecondFactorAuthenticationTimeout=yes",
                "ReloginAfterSecondFactorAuthenticationTimeout=yes"
            ).replace(
                "ExitAfterSecondFactorAuthenticationTimeout=no",
                "ExitAfterSecondFactorAuthenticationTimeout=no"
            )

            # Add or enhance logging settings
            if "LogStructureWhen=always" not in enhanced_config:
                enhanced_config += "\n# Enhanced logging\nLogStructureWhen=always\n"

            # Write enhanced config
            with open(self.ibc_config, 'w') as f:
                f.write(enhanced_config)

            self.logger.info("✅ IBC configuration enhanced")
            return True

        except Exception as e:
            self.logger.error(f"❌ IBC config enhancement failed: {e}")
            return False

    def start_ibc_gateway(self) -> bool:
        """Start IB Gateway using IBC"""
        try:
            self.logger.info("🚀 Starting IB Gateway with IBC...")

            # Build IBC command
            cmd = [
                "java",
                "-cp", f"{self.ibc_jar}:/home/davidsanker/IBGateway/jars/*",
                "ibcalpha.ibc.IbcGateway",
                self.ibc_config,
                "paper",
                "-inline"
            ]

            # Start IBC
            env = os.environ.copy()
            env["DISPLAY"] = ":1"

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.logger.info(f"✅ IBC started with PID: {process.pid}")
            return True

        except Exception as e:
            self.logger.error(f"❌ IBC start failed: {e}")
            return False

    def wait_for_api_port(self) -> bool:
        """Wait for API port to become available"""
        self.logger.info(f"⏳ Waiting for API port {self.port} (timeout: {self.max_wait_time}s)...")

        start_time = time.time()

        while time.time() - start_time < self.max_wait_time:
            try:
                # Test port connectivity
                result = subprocess.run(
                    ["nc", "-z", "127.0.0.1", str(self.port)],
                    capture_output=True,
                    timeout=5
                )

                if result.returncode == 0:
                    elapsed = int(time.time() - start_time)
                    self.logger.info(f"✅ API port {self.port} is ready after {elapsed}s!")
                    return True

            except:
                pass

            # Log progress every 30 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0 and elapsed > 0:
                self.logger.info(f"⏳ Still waiting for API port... ({elapsed}s elapsed)")

            time.sleep(5)

        self.logger.error(f"❌ API port {self.port} not ready after {self.max_wait_time}s")
        return False

    def test_api_connection(self) -> bool:
        """Test API connection with ib_insync"""
        try:
            self.logger.info("🔗 Testing API connection...")

            test_script = '''
import sys
sys.path.append("/home/davidsanker/trading_bot_venv/lib/python3.11/site-packages")
from ib_insync import IB

ib = IB()
try:
    ib.connect("127.0.0.1", 4002, clientId=9999, timeout=30)
    print("✅ API connection successful!")
    server_time = ib.reqCurrentTime()
    print(f"✅ Server time: {server_time}")
    ib.disconnect()
    sys.exit(0)
except Exception as e:
    print(f"❌ API connection failed: {e}")
    sys.exit(1)
'''

            result = subprocess.run(
                ["python3", "-c", test_script],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.logger.info("✅ API connection verified!")
                self.logger.info(f"API Response: {result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"❌ API verification failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"❌ API verification error: {e}")
            return False

    def create_status_file(self, success: bool):
        """Create status file for monitoring"""
        status = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "api_ready": success,
            "port": self.port,
            "pid": os.getpid()
        }

        with open("/tmp/ib_gateway_status.json", "w") as f:
            import json
            json.dump(status, f, indent=2)

    def auto_start(self) -> bool:
        """Main auto-start process"""
        self.logger.info("🎯 Starting IB Gateway auto-start process...")

        # Step 1: Clean up existing processes
        if not self.kill_existing_processes():
            return False

        # Step 2: Enhance IBC configuration
        if not self.enhance_ibc_config():
            return False

        # Step 3: Start IBC Gateway
        if not self.start_ibc_gateway():
            return False

        # Step 4: Wait for API port
        if not self.wait_for_api_port():
            return False

        # Step 5: Test API connection
        if not self.test_api_connection():
            return False

        # Step 6: Create status file
        self.create_status_file(True)

        self.logger.info("🎉 IB Gateway auto-start completed successfully!")
        return True

def main():
    """Main entry point"""
    auto_starter = IBGatewayAutoStart()

    try:
        success = auto_starter.auto_start()

        if success:
            print("🎉 IB Gateway auto-start successful!")
            print("🔗 API is ready for trading bot connections")
            print("📊 Trading bot can now be started")
            print("📋 Status saved to /tmp/ib_gateway_status.json")
        else:
            print("❌ IB Gateway auto-start failed")
            print("🔧 Check logs for detailed error information")

        return success

    except KeyboardInterrupt:
        print("⏹️ Auto-start process interrupted")
        return False
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)