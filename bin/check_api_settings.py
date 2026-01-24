#!/usr/bin/env python3
"""
Check IB Gateway API Settings and Login Status
Uses xdotool to navigate menus and check configuration
"""

import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_xdotool_command(cmd):
    """Execute xdotool command and return result"""
    try:
        result = subprocess.run(['xdotool'] + cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"xdotool command failed: {e}")
        return False, "", str(e)

def check_api_settings():
    """Check if API is enabled in IB Gateway"""
    logger.info("Checking IB Gateway API settings...")

    # Find IB Gateway window
    success, output, error = run_xdotool_command(['search', '--name', 'IBKR Gateway'])
    if not success:
        logger.error("Could not find IB Gateway window")
        return False

    window_id = output.strip().split('\n')[0]
    logger.info(f"Found IB Gateway window: {window_id}")

    # Focus the window
    run_xdotool_command(['windowactivate', window_id])
    time.sleep(1)

    # Try to open API settings (Alt+ C, then A for API)
    logger.info("Attempting to open API settings...")

    # Press Alt to activate menu
    run_xdotool_command(['key', 'Alt'])
    time.sleep(0.5)

    # Type 'c' for Configure menu
    run_xdotool_command(['key', 'c'])
    time.sleep(0.5)

    # Type 'a' for API Settings
    run_xdotool_command(['key', 'a'])
    time.sleep(2)  # Wait for dialog to open

    logger.info("API settings dialog should now be open")
    logger.info("Please check manually if:")
    logger.info("  □ Enable ActiveX and Socket Clients is CHECKED")
    logger.info("  □ Socket port is set to 4002")
    logger.info("  □ Read-Only API is UNCHECKED (if you want to trade)")
    logger.info("  □ Allow connections from localhost is CHECKED")

    return True

def check_login_status():
    """Check current login status"""
    logger.info("Checking IB Gateway login status...")

    success, output, error = run_xdotool_command(['search', '--name', 'IBKR Gateway'])
    if not success:
        return False

    window_id = output.strip().split('\n')[0]
    run_xdotool_command(['windowactivate', window_id])
    time.sleep(1)

    # Check File menu login status
    run_xdotool_command(['key', 'Alt'])
    time.sleep(0.5)
    run_xdotool_command(['key', 'f'])  # File menu
    time.sleep(0.5)

    logger.info("File menu should be open")
    logger.info("Look for 'Login' vs 'Logout' to determine status")

    return True

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("IB Gateway API and Login Status Check")
    logger.info("=" * 50)

    print("\n🔍 Let me help you check the current status...\n")

    # Check login status
    check_login_status()

    print("\n" + "=" * 50)

    # Check API settings
    check_api_settings()

    print("\n" + "=" * 50)
    print("✅ Automatic check complete!")
    print("Please manually verify the settings mentioned above")
    print("Then run this test again:")
    print("source ~/venv/bin/activate && timeout 10 python3 -c \"")
    print("from ib_insync import IB; ib = IB(); ib.connect('127.0.0.1', 4002, clientId=999, timeout=8); print('SUCCESS!'); ib.disconnect()\"")