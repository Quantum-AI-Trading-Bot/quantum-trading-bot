#!/usr/bin/env python3
"""
Comprehensive IB Gateway Authentication Fix
Addresses chronic authentication and API connection issues
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class IBGatewayAuthFix:
    """Comprehensive fix for IB Gateway authentication issues"""

    def __init__(self):
        self.log_dir = "/home/davidsanker/platform/logs/ib-gateway"
        os.makedirs(self.log_dir, exist_ok=True)

    def diagnose_issue(self):
        """Diagnose the specific authentication issue"""
        logger.info("🔍 DIAGNOSING IB Gateway Authentication Issue")

        # Check 1: Process status
        logger.info("1. Checking IB Gateway process...")
        try:
            result = subprocess.run(['pgrep', '-f', 'ibgateway'], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                logger.info(f"   ✓ IB Gateway running (PIDs: {', '.join(pids)})")
            else:
                logger.error("   ❌ IB Gateway not running")
                return "no_process"
        except Exception as e:
            logger.error(f"   ❌ Process check failed: {e}")

        # Check 2: Port status
        logger.info("2. Checking API port 4002...")
        try:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
            if '4002' in result.stdout:
                logger.info("   ✓ Port 4002 is listening")
            else:
                logger.error("   ❌ Port 4002 not listening")
                return "port_not_listening"
        except Exception as e:
            logger.error(f"   ❌ Port check failed: {e}")

        # Check 3: VNC display
        logger.info("3. Checking VNC display...")
        try:
            result = subprocess.run(['DISPLAY=:1', 'xwininfo', '-tree', '-root'],
                                  capture_output=True, text=True)
            if 'Warning' in result.stdout:
                logger.warning("   ⚠️  Warning dialog detected in VNC")
            if 'Login' in result.stdout:
                logger.info("   ✓ Login elements visible")
            else:
                logger.warning("   ⚠️  No login elements found")
        except Exception as e:
            logger.error(f"   ❌ VNC check failed: {e}")

        return "needs_auth_check"

    def apply_session_conflict_fix(self):
        """Apply the session conflict fix - most common chronic issue"""
        logger.info("🔧 APPLYING SESSION CONFLICT FIX")

        try:
            # Kill all Java processes
            logger.info("   Stopping all Java processes...")
            subprocess.run(['pkill', '-f', 'java'], check=False)
            time.sleep(3)

            # Clean temp files
            logger.info("   Cleaning temporary files...")
            temp_files = ['/home/davidsanker/IBGateway/*.tmp', '/home/davidsanker/IBGateway/*.lock']
            for pattern in temp_files:
                subprocess.run(['rm', '-f'] + pattern.split(), check=False)

            # Wait for cleanup
            time.sleep(2)
            logger.info("   ✓ Session cleanup complete")

            return True

        except Exception as e:
            logger.error(f"   ❌ Session cleanup failed: {e}")
            return False

    def start_clean_gateway(self):
        """Start a clean IB Gateway instance"""
        logger.info("🚀 STARTING CLEAN IB GATEWAY")

        try:
            # Start Gateway with VNC display
            cmd = ['DISPLAY=:1', '/home/davidsanker/IBGateway/ibgateway.bin']
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            logger.info("   ✓ IB Gateway starting...")
            logger.info("   ⏳ Waiting for initialization (this may take 60-90 seconds)...")

            # Wait for port to open
            max_wait = 120  # 2 minutes
            for i in range(max_wait):
                result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
                if '4002' in result.stdout:
                    logger.info(f"   ✓ API port 4002 open after {i+1} seconds")
                    return True
                time.sleep(1)

            logger.error("   ❌ Port 4002 never opened")
            return False

        except Exception as e:
            logger.error(f"   ❌ Gateway start failed: {e}")
            return False

    def test_api_connection(self):
        """Test API connection with comprehensive error reporting"""
        logger.info("🧪 TESTING API CONNECTION")

        test_script = '''
import sys
try:
    from ib_insync import IB
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=15)
    accounts = ib.managedAccounts()
    print(f"SUCCESS: Connected with accounts: {accounts}")
    ib.disconnect()
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    sys.exit(1)
'''

        try:
            result = subprocess.run([
                'source', '~/venv/bin/activate', '&&',
                'python3', '-c', test_script
            ], shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"   ✅ {result.stdout.strip()}")
                return True
            else:
                logger.error(f"   ❌ {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("   ❌ API connection test timed out")
            return False
        except Exception as e:
            logger.error(f"   ❌ Test failed: {e}")
            return False

    def provide_manual_instructions(self):
        """Provide manual instructions for VNC access"""
        logger.info("📋 MANUAL VNC INSTRUCTIONS")
        print("""

🖥️  VNC ACCESS STEPS:
1. Connect to VNC: vnc://localhost:5901
2. Username: amakua444, Password: Twbb19874!

⚙️  IB GATEWAY CONFIGURATION:
1. If you see a warning dialog → Click "OK" or "Dismiss"
2. Login to IB Gateway with your credentials
3. Go to: Configure → API → Settings
4. CHECK these settings:
   ☑ Enable ActiveX and Socket Clients
   ☑ Socket port: 4002
   ☑ Read-Only API: UNCHECKED (for trading)
   ☑ Allow connections from localhost
5. Click "OK" to save

🔄 AFTER CONFIGURATION:
Run this command to test:
source ~/venv/bin/activate && timeout 10 python3 -c "
from ib_insync import IB;
ib = IB();
ib.connect('127.0.0.1', 4002, clientId=999, timeout=8);
print('SUCCESS! API working!');
ib.disconnect()
"

        """)

    def run_comprehensive_fix(self):
        """Run the complete authentication fix sequence"""
        logger.info("=" * 60)
        logger.info("🔧 COMPREHENSIVE IB GATEWAY AUTHENTICATION FIX")
        logger.info("=" * 60)

        # Step 1: Diagnose
        diagnosis = self.diagnose_issue()
        logger.info(f"Diagnosis: {diagnosis}")

        if diagnosis == "no_process":
            logger.info("IB Gateway not running - starting fresh...")
            return self.start_clean_gateway()

        # Step 2: Apply session conflict fix
        if not self.apply_session_conflict_fix():
            logger.error("Session conflict fix failed")
            return False

        # Step 3: Start clean Gateway
        if not self.start_clean_gateway():
            logger.error("Failed to start clean Gateway")
            return False

        # Step 4: Test API
        if not self.test_api_connection():
            logger.warning("API test failed - manual configuration may be needed")
            self.provide_manual_instructions()
            return False

        logger.info("🎉 SUCCESS! IB Gateway authentication and API working")
        return True

if __name__ == "__main__":
    fix = IBGatewayAuthFix()
    success = fix.run_comprehensive_fix()

    if success:
        print("\n✅ IB Gateway authentication fix completed successfully!")
        print("Your Quantum trading bot should now be able to connect.")
    else:
        print("\n⚠️  Manual intervention required via VNC")
        print("Please follow the manual instructions above.")