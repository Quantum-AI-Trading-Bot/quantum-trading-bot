#!/usr/bin/env python3
"""
IB Gateway Automated Login System
Enhanced with VNC/X11 automation and smart retry logic
"""

import subprocess
import time
import logging
from typing import Optional, Dict, List
import os
import signal
import sys

class IBGatewayAutomator:
    """Complete IB Gateway automation with VNC/X11"""

    def __init__(self):
        self.display = ":1"
        self.vnc_port = "5901"
        self.credentials = {
            "username": "amakua444",
            "password": "Twbb19874!"
        }
        self.max_attempts = 5
        self.attempt_count = 0

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start_vnc_server(self) -> bool:
        """Start VNC server for GUI access"""
        try:
            self.logger.info("🖥️ Starting VNC server...")

            # Kill any existing VNC processes
            subprocess.run(["pkill", "-f", "x11vnc"], check=False)
            time.sleep(2)

            cmd = [
                "x11vnc",
                "-display", self.display,
                "-forever",
                "-nopw",
                "-quiet",
                "-create",
                "-bg"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            time.sleep(3)

            self.logger.info(f"✅ VNC server started on localhost:{self.vnc_port}")
            return True

        except Exception as e:
            self.logger.error(f"❌ VNC server failed: {e}")
            return False

    def detect_gateway_window(self) -> Optional[str]:
        """Detect IB Gateway window using xdotool"""
        try:
            # Wait a moment for windows to appear
            time.sleep(2)

            # Try multiple search patterns
            search_patterns = [
                ["xdotool", "search", "--class", "Gateway"],
                ["xdotool", "search", "--name", "Gateway"],
                ["xdotool", "search", "--name", "IB Gateway"],
                ["xdotool", "search", "--name", "Login"]
            ]

            for pattern in search_patterns:
                try:
                    result = subprocess.run(pattern, capture_output=True, text=True, timeout=10)

                    if result.stdout.strip():
                        window_id = result.stdout.strip().split('\n')[0]
                        self.logger.info(f"✅ Found Gateway window: {window_id}")
                        return window_id
                except:
                    continue

            # If no Gateway window, try to find any window that might be login-related
            self.logger.info("🔍 Searching for any login-related windows...")
            try:
                cmd = ["xdotool", "search", "--name", ""]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.stdout.strip():
                    windows = result.stdout.strip().split('\n')
                    for window_id in windows:
                        # Get window name
                        name_cmd = ["xdotool", "getwindowname", window_id]
                        name_result = subprocess.run(name_cmd, capture_output=True, text=True, timeout=5)

                        if name_result.stdout.strip():
                            window_name = name_result.stdout.strip().lower()
                            if any(keyword in window_name for keyword in ["login", "gateway", "ib", "trading"]):
                                self.logger.info(f"✅ Found potential login window: {window_name} ({window_id})")
                                return window_id
            except:
                pass

            self.logger.warning("❌ IB Gateway window not found")
            return None

        except Exception as e:
            self.logger.error(f"❌ Window detection failed: {e}")
            return None

    def activate_window(self, window_id: str) -> bool:
        """Activate and bring window to front"""
        try:
            self.logger.info(f"🪟 Activating window {window_id}")

            # Multiple activation methods
            commands = [
                ["xdotool", "windowactivate", window_id],
                ["xdotool", "windowraise", window_id],
                ["xdotool", "windowfocus", window_id]
            ]

            for cmd in commands:
                subprocess.run(cmd, capture_output=True, stderr=subprocess.DEVNULL)
                time.sleep(0.5)

            time.sleep(2)  # Wait for activation
            return True

        except Exception as e:
            self.logger.error(f"❌ Window activation failed: {e}")
            return False

    def enter_credentials(self, window_id: str) -> bool:
        """Enter login credentials using xdotool"""
        try:
            self.logger.info("🔐 Entering credentials...")

            # Ensure window is active
            self.activate_window(window_id)

            # Clear any existing text and enter username
            self.logger.info("📝 Entering username...")
            subprocess.run(["xdotool", "key", "Ctrl+a"], check=False)
            time.sleep(0.5)
            subprocess.run(["xdotool", "type", self.credentials["username"]], check=False)
            time.sleep(0.5)

            # Tab to password field
            self.logger.info("⇾ Moving to password field...")
            subprocess.run(["xdotool", "key", "Tab"], check=False)
            time.sleep(0.5)

            # Enter password
            self.logger.info("🔑 Entering password...")
            subprocess.run(["xdotool", "type", self.credentials["password"]], check=False)
            time.sleep(0.5)

            # Submit login
            self.logger.info("🚀 Submitting login...")
            subprocess.run(["xdotool", "key", "Return"], check=False)

            self.logger.info("✅ Credentials entered - waiting for 2FA...")
            return True

        except Exception as e:
            self.logger.error(f"❌ Credential entry failed: {e}")
            return False

    def handle_login_dialogs(self) -> bool:
        """Handle various login dialogs and warnings"""
        try:
            self.logger.info("🪟 Checking for login dialogs...")

            # Look for common dialog windows
            dialog_patterns = [
                "Login Messages",
                "Paper Trading Account",
                "Configuration",
                "Warning",
                "Notice",
                "Session"
            ]

            for pattern in dialog_patterns:
                cmd = ["xdotool", "search", "--name", pattern]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.stdout.strip():
                    window_id = result.stdout.strip().split('\n')[0]
                    self.logger.info(f"🪟 Found dialog: {pattern}")

                    # Activate dialog
                    self.activate_window(window_id)

                    # Handle dialog (space to accept, return to confirm)
                    if "Warning" in pattern or "Paper Trading" in pattern:
                        subprocess.run(["xdotool", "key", "space"], check=False)
                        time.sleep(1)
                        subprocess.run(["xdotool", "key", "Return"], check=False)
                    else:
                        subprocess.run(["xdotool", "key", "Return"], check=False)

                    time.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"❌ Dialog handling failed: {e}")
            return False

    def wait_for_api_ready(self, timeout: int = 180) -> bool:
        """Wait for IB Gateway API to be ready"""
        self.logger.info(f"⏳ Waiting for API port 4002 (timeout: {timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Test if port is listening
                result = subprocess.run(
                    ["nc", "-z", "127.0.0.1", "4002"],
                    capture_output=True,
                    timeout=5
                )

                if result.returncode == 0:
                    self.logger.info("✅ API port 4002 is ready!")
                    return True

            except:
                pass

            time.sleep(5)
            elapsed = int(time.time() - start_time)
            if elapsed % 15 == 0:  # Log every 15 seconds
                self.logger.info(f"⏳ Still waiting for API port... ({elapsed}s)")

        self.logger.error("❌ API port not ready after timeout")
        return False

    def verify_api_connection(self) -> bool:
        """Verify API connection with ib_insync"""
        try:
            self.logger.info("🔗 Testing API connection...")

            test_script = '''
import sys
sys.path.append("/home/davidsanker/trading_bot_venv/lib/python3.11/site-packages")
from ib_insync import IB
import time

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

            self.logger.info(f"API Test Result: {result.stdout.strip()}")
            if result.stderr.strip():
                self.logger.warning(f"API Test Warning: {result.stderr.strip()}")

            if result.returncode == 0:
                self.logger.info("✅ API connection verified!")
                return True
            else:
                self.logger.error(f"❌ API verification failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"❌ API verification error: {e}")
            return False

    def start_ib_gateway_manual(self) -> bool:
        """Start IB Gateway manually if IBC failed"""
        try:
            self.logger.info("🚀 Starting IB Gateway manually...")

            # Kill existing IB Gateway processes
            subprocess.run(["pkill", "-f", "ibgateway"], check=False)
            subprocess.run(["pkill", "-f", "IBC.jar"], check=False)
            time.sleep(3)

            # Start IB Gateway with GUI
            env = os.environ.copy()
            env["DISPLAY"] = self.display

            cmd = [
                "/home/davidsanker/IBGateway/ibgateway.bin"
            ]

            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.info("✅ IB Gateway started manually")

            # Wait for window to appear
            time.sleep(10)
            return True

        except Exception as e:
            self.logger.error(f"❌ Manual IB Gateway start failed: {e}")
            return False

    def login_attempt(self) -> bool:
        """Single login attempt"""
        self.attempt_count += 1
        self.logger.info(f"🚀 Login attempt {self.attempt_count}/{self.max_attempts}")

        # Step 1: Start IB Gateway if needed
        if not self.detect_gateway_window():
            self.logger.info("🔄 IB Gateway not found, starting manually...")
            if not self.start_ib_gateway_manual():
                self.logger.error("❌ Cannot start IB Gateway")
                return False

        # Step 2: Detect Gateway window
        window_id = self.detect_gateway_window()
        if not window_id:
            self.logger.error("❌ Cannot find Gateway window")
            return False

        # Step 3: Activate window
        if not self.activate_window(window_id):
            self.logger.error("❌ Cannot activate Gateway window")
            return False

        # Step 4: Enter credentials
        if not self.enter_credentials(window_id):
            self.logger.error("❌ Cannot enter credentials")
            return False

        # Step 5: Handle dialogs
        time.sleep(5)  # Wait for dialogs to appear
        self.handle_login_dialogs()

        # Step 6: Wait for API to be ready
        if not self.wait_for_api_ready():
            self.logger.error("❌ API not ready after login")
            return False

        # Step 7: Verify API connection
        if not self.verify_api_connection():
            self.logger.error("❌ API connection verification failed")
            return False

        return True

    def automated_login(self) -> bool:
        """Main automated login process with retry logic"""
        self.logger.info("🎯 Starting automated IB Gateway login...")

        # Start VNC server
        if not self.start_vnc_server():
            self.logger.warning("⚠️ VNC server failed, continuing without it...")

        # Multiple login attempts
        while self.attempt_count < self.max_attempts:
            try:
                if self.login_attempt():
                    self.logger.info("🎉 Automated login successful!")
                    return True

                # Wait before retry
                if self.attempt_count < self.max_attempts:
                    wait_time = 30 * self.attempt_count
                    self.logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                self.logger.info("⏹️ Login process interrupted")
                return False
            except Exception as e:
                self.logger.error(f"❌ Login attempt failed: {e}")

        self.logger.error("❌ All login attempts failed")
        return False

    def stop_vnc_server(self):
        """Stop VNC server"""
        try:
            subprocess.run(["pkill", "-f", "x11vnc"], check=False)
            self.logger.info("🛑 VNC server stopped")
        except:
            pass

def main():
    """Main entry point"""
    automator = IBGatewayAutomator()

    try:
        success = automator.automated_login()

        if success:
            print("🎉 IB Gateway login completed successfully!")
            print("🔗 API is ready for trading bot connections")
            print("📊 Trading bot can now be started")
            print("🌐 VNC access available at localhost:5901")
        else:
            print("❌ Automated login failed")
            print("🔧 Manual intervention may be required")
            print("💻 Connect via VNC localhost:5901 for manual login")

        return success

    finally:
        # Keep VNC running for debugging
        # automator.stop_vnc_server()
        pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)