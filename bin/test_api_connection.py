#!/usr/bin/env python3

import socket
import time
import sys

def test_api_connection():
    """Test IB Gateway API connection on port 4002"""
    print("🔍 Testing IB Gateway API Connection...")
    print("=====================================")

    host = '127.0.0.1'
    port = 4002
    timeout = 5

    try:
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        print(f"📡 Connecting to {host}:{port}...")
        result = sock.connect_ex((host, port))

        if result == 0:
            print("✅ Connection successful!")

            # Try to send API test message
            test_msg = b"\x00\x00\x00\x01"  # Minimal API message
            sock.send(test_msg)

            # Wait for response
            time.sleep(1)

            try:
                response = sock.recv(1024)
                if response:
                    print(f"✅ API responded with {len(response)} bytes")
                    print(f"   Response: {response[:50]}...")
                    return True
                else:
                    print("⚠️  No response from API (might need login)")
                    return False
            except socket.timeout:
                print("⏳ API connected but no response (login required)")
                return False

        else:
            print(f"❌ Connection failed with error code {result}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        sock.close()

def check_process_status():
    """Check if IB Gateway process is running"""
    import subprocess

    try:
        result = subprocess.run(['pgrep', '-f', 'ibgateway'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ IB Gateway processes running: {len(pids)}")
            for pid in pids:
                print(f"   PID: {pid}")
            return True
        else:
            print("❌ No IB Gateway process found")
            return False
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
        return False

if __name__ == "__main__":
    print("🚀 IB Gateway API Status Check")
    print("=============================\n")

    # Check process status
    process_ok = check_process_status()
    print()

    # Test API connection
    if process_ok:
        api_ok = test_api_connection()

        if api_ok:
            print("\n🎯 RESULT: API is ready for trading bot connections!")
            sys.exit(0)
        else:
            print("\n⚠️  RESULT: Gateway running but API needs login via VNC")
            print("   Connect to VNC and complete the login process")
            sys.exit(1)
    else:
        print("\n❌ RESULT: Gateway not running - start it first")
        sys.exit(2)