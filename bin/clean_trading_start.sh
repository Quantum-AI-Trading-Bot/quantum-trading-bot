#!/bin/bash

echo "🧹 Complete Clean Trading System Restart"
echo "======================================"

# Clean up any existing processes
echo "🔄 Terminating all existing processes..."
pkill -9 -f java 2>/dev/null
pkill -9 -f ibgateway 2>/dev/null
pkill -9 -f vncserver 2>/dev/null
pkill -9 -f Xvnc 2>/dev/null
pkill -9 -f fluxbox 2>/dev/null

# Kill any VNC sessions
vncserver -kill :1 2>/dev/null
vncserver -kill :2 2>/dev/null
vncserver -kill :0 2>/dev/null

# Remove lock files
rm -f /tmp/.X1-lock
rm -f /tmp/.X0-lock
rm -f /tmp/.X11-unix/X1
rm -f /tmp/.X11-unix/X0

# Clean Gateway session files
rm -f /home/davidsanker/IBGateway/*.lock
rm -f /home/davidsanker/Jts/*.lock

echo "✅ All processes terminated"

# Wait for cleanup
sleep 3

# Set up clean environment
export DISPLAY=:1

# Start fresh VNC server
echo "🖥️  Starting clean VNC server on display :1"
vncserver :1 -geometry 1024x768 -depth 24 -localhost no > /dev/null 2>&1 &
sleep 2

# Start Fluxbox window manager
echo "🪟 Starting window manager"
fluxbox > /dev/null 2>&1 &
sleep 2

# Ensure Gateway config is optimal
echo "📋 Configuring Gateway for trading..."
cat > /home/davidsanker/IBGateway/jts.ini << 'EOF'
[IBGateway]
ApiEnabled=1
ReadOnlyApi=0
WriteDebug=false
AutoStartApi=1
AcceptIncomingConnection=1
ApiAutoAccept=1
LocalServerPort=4000
SocketPort=4002
TrustedIPs=127.0.0.1
ApiOnly=false
TrustLocalhost=1
MainWindow.Width=900
MainWindow.Height=700
MinimizeMainWindow=false

[Logon]
useRemoteSettings=false
tradingMode=s
colorPalletName=dark
Locale=en
os_titlebar=false
SupportsSSL=ndc1.ibllc.com:4000,true,20251111,false
UseSSL=true
screenHeight=768
ibkrBranding=pro

[Communication]
ctciAutoEncrypt=true
Peer=ndc1.ibllc.com:4001
Region=usr
EOF

echo "✅ Configuration complete"

# Start Gateway
echo "🚀 Starting IB Gateway..."
cd /home/davidsanker/IBGateway
export DISPLAY=:1
./ibgateway.bin &

# Wait for startup
echo "⏳ Waiting for Gateway to initialize..."
sleep 15

# Check if Gateway is running
if pgrep -f "ibgateway" > /dev/null; then
    echo "✅ IB Gateway started successfully!"

    # Check API port
    sleep 5
    if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" > /dev/null 2>&1; then
        echo "✅ API Port 4002 is responding!"
    else
        echo "⏳ API Port 4002 ready - needs login activation"
    fi

    echo ""
    echo "🎯 SYSTEM READY FOR SINGLE VNC SESSION:"
    echo "   VNC: vncviewer 35.232.64.211:5901"
    echo "   Port: 5901 (only one session)"
    echo ""
    echo "⚠️  LOGIN INSTRUCTIONS:"
    echo "1. Connect via VNC above"
    echo "2. Login with your IBKR credentials"
    echo "3. Ensure 'Enable ActiveX and Socket Clients' is CHECKED"
    echo "4. Ensure 'Read-Only API' is UNCHECKED"
    echo "5. Click OK to save API settings"
    echo ""
    echo "🤖 After login, the trading bot will connect and start!"

else
    echo "❌ Failed to start IB Gateway"
    exit 1
fi