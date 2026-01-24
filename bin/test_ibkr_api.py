#!/usr/bin/env python3

"""
Simple IBKR API Test Client
Tests connectivity to IB Gateway on port 4002
"""

import socket
import time
import sys

def create_api_client():
    """Create a simple test client for IB API"""
    print("🔌 Creating IB API Test Client...")

    host = '127.0.0.1'
    port = 4002

    try:
        # Connect to Gateway
        print(f"📡 Connecting to IB Gateway at {host}:{port}")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        client.connect((host, port))
        print("✅ Connected to IB Gateway!")

        # Send a simple API message (version handshake)
        # This is a minimal API message to test the connection
        api_msg = b'\x00\x00\x00\x01'  # API version message
        client.send(api_msg)
        print("📨 Sent API handshake message")

        # Wait for response
        time.sleep(1)

        try:
            response = client.recv(1024)
            if response:
                print(f"✅ Received response: {len(response)} bytes")
                print(f"   Raw data: {response}")
                return True
            else:
                print("⚠️  No response received (login may be required)")
                return False
        except socket.timeout:
            print("⏳ Response timeout (Gateway may need login)")
            return False

    except ConnectionRefusedError:
        print("❌ Connection refused - Gateway may not be ready")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        try:
            client.close()
            print("🔌 Connection closed")
        except:
            pass

def test_trading_readiness():
    """Check if system is ready for trading"""
    print("\n🎯 Trading Readiness Check")
    print("=" * 30)

    # Check Gateway process
    import subprocess
    try:
        result = subprocess.run(['pgrep', '-f', 'ibgateway'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ IB Gateway process: RUNNING")
        else:
            print("❌ IB Gateway process: NOT RUNNING")
            return False
    except:
        print("❌ Could not check Gateway process")
        return False

    # Test API connection
    if create_api_client():
        print("✅ API Connection: READY")
        return True
    else:
        print("⚠️  API Connection: NEEDS LOGIN")
        return False

if __name__ == "__main__":
    print("🚀 IBKR Trading System Test")
    print("=" * 30)

    ready = test_trading_readiness()

    if ready:
        print("\n🎉 SUCCESS: System is ready for trading!")
        print("   The Quantim AI Trading Bot can now connect.")
        sys.exit(0)
    else:
        print("\n⚠️  ACTION NEEDED: Complete login via VNC first")
        print("   VNC: vncviewer 35.232.64.211:5901")
        sys.exit(1)