#!/bin/bash

echo "🔧 Starting IB Gateway with Manual Trading API Configuration..."
echo "=========================================================="

# Kill any existing processes
echo "🔄 Cleaning up existing processes..."
pkill -f "ibgateway" 2>/dev/null
pkill -f "IBC" 2>/dev/null
pkill -f "java.*ibc" 2>/dev/null
sleep 2

# Check VNC is running
echo "🖥️  Checking VNC server..."
pgrep -f "vncserver" > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  VNC server not running - starting it..."
    vncserver :1 -geometry 1024x768 -depth 24 > /dev/null 2>&1 &
    sleep 2
fi

# Ensure Display is set
export DISPLAY=:1

# Start Fluxbox if not running
echo "🪟 Starting Fluxbox window manager..."
pgrep -f "fluxbox" > /dev/null
if [ $? -ne 0 ]; then
    fluxbox > /dev/null 2>&1 &
    sleep 2
fi

# Clean up any existing sessions
echo "🧹 Cleaning up previous sessions..."
rm -f /home/davidsanker/IBGateway/*.lock
rm -f /home/davidsanker/Jts/*.lock

# Create final API configuration
echo "📋 Creating optimal API configuration..."
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
MainWindow.Width=800
MainWindow.Height=600

[Logon]
useRemoteSettings=false
TimeZone=Africa/Abidjan
tradingMode=s
colorPalletName=dark
Steps=5
Locale=en
os_titlebar=false
SupportsSSL=ndc1.ibllc.com:4000,true,20251111,false
UseSSL=true
screenHeight=768
s3store=true
displayedproxymsg=1
ibkrBranding=pro

[Communication]
ctciAutoEncrypt=true
Peer=ndc1.ibllc.com:4001
Region=usr
EOF

# Start Gateway manually
echo "🚀 Starting IB Gateway with LIVE trading mode..."
echo "   API will be enabled on port 4002"
echo "   Window should be visible via VNC on port 5901"
echo ""
echo "📝 IMPORTANT INSTRUCTIONS:"
echo "1. Connect via VNC: vncviewer 35.232.64.211:5901"
echo "2. Login with your IBKR credentials"
echo "3. Ensure 'Enable ActiveX and Socket Clients' is CHECKED"
echo "4. Ensure 'Read-Only API' is UNCHECKED"
echo "5. Click 'OK' to save API configuration"
echo ""

cd /home/davidsanker/IBGateway
./ibgateway.bin &

# Wait for startup
echo "⏳ Waiting for Gateway to start..."
sleep 10

# Check if process is running
pgrep -f "ibgateway" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ IB Gateway started successfully!"
    echo "🌐 API Status:"
    echo "   - Port 4002 should be open after login"
    echo "   - Trading API: ENABLED (not read-only)"
    echo "   - Ready for client connections"

    # Test API port
    sleep 5
    if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" > /dev/null 2>&1; then
        echo "✅ API port 4002 is responding - ready for trading bot!"
    else
        echo "⚠️  API port 4002 not yet responding - login via VNC first"
    fi
else
    echo "❌ Failed to start IB Gateway"
    exit 1
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Login via VNC now"
echo "2. Verify API configuration in Gateway"
echo "3. Test trading bot connection"
echo "4. Monitor: tail -f /home/davidsanker/IBGateway/gateway.log"