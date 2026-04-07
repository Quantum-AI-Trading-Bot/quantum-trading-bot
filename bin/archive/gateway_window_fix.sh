#!/bin/bash

# Gateway Window Visibility Fix
# Forces IB Gateway window to appear and handles login automatically

set -e

echo "=========================================="
echo "IB Gateway Window Fix"
echo "=========================================="

# Kill any existing Gateway processes
echo "🔄 Cleaning up existing processes..."
pkill -f "java.*ibgateway" || true
pkill -f "IBC.jar" || true
sleep 2

# Set display
export DISPLAY=:1

# Check VNC is running
echo "📺 Checking VNC display..."
if ! xwininfo -root >/dev/null 2>&1; then
    echo "❌ VNC display not available"
    exit 1
fi
echo "✅ VNC display is available"

# Start Gateway in background
echo "🚀 Starting IB Gateway..."
cd /home/davidsanker/IBGateway

# Use the original startup script with all necessary flags
java --add-opens=java.desktop/javax.swing=ALL-UNNAMED \
     --add-opens=java.desktop/java.awt=ALL-UNNAMED \
     --add-opens=java.desktop/javax.swing.plaf=ALL-UNNAMED \
     --add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
     -DjtsConfigDir=/home/davidsanker/IBGateway \
     -cp "jars/*:1037/jars/*:.install4j/*" \
     ibgateway.GWClient &

GATEWAY_PID=$!
echo "✅ Gateway started (PID: $GATEWAY_PID)"

# Wait for window to appear
echo "⏳ Waiting for Gateway window..."
sleep 10

# Function to force window visibility
force_window_visibility() {
    echo "🔍 Looking for Gateway window..."

    # Try to find and map the window
    for i in {1..30}; do
        WINDOW_ID=$(DISPLAY=:1 xwininfo -tree -root | grep -i "gateway\|ibkr\|install4j-ibgateway" | head -1 | grep -o "0x[0-9a-f]*" | head -1)

        if [ ! -z "$WINDOW_ID" ]; then
            echo "🎯 Found Gateway window: $WINDOW_ID"

            # Force window to be visible and mapped
            DISPLAY=:1 xdotool windowmap "$WINDOW_ID" 2>/dev/null || true
            DISPLAY=:1 xdotool windowraise "$WINDOW_ID" 2>/dev/null || true
            DISPLAY=:1 xdotool windowmove "$WINDOW_ID" 50 50 2>/dev/null || true
            DISPLAY=:1 xdotool windowsize "$WINDOW_ID" 800 600 2>/dev/null || true

            # Try alternative methods
            DISPLAY=:1 xprop -id "$WINDOW_ID" -f _NET_WM_STATE 32a \
                -set _NET_WM_STATE _NET_WM_STATE_ABOVE, _NET_WM_STATE_FOCUSED, _NET_WM_STATE_DEMANDS_ATTENTION 2>/dev/null || true

            echo "✅ Window visibility forced"
            return 0
        fi

        sleep 1
    done

    echo "⚠️  Gateway window not found after 30 seconds"
    return 1
}

# Try to force window visibility
force_window_visibility

# Additional window management tricks
echo "🪄 Applying window management tricks..."

# Install xdotool if not available (though it should be)
if ! command -v xdotool >/dev/null 2>&1; then
    echo "📦 Installing xdotool..."
    sudo apt-get update -qq && sudo apt-get install -y xdotool >/dev/null 2>&1 || true
fi

# Try to list all windows and force Gateway to front
echo "📋 Listing all windows..."
DISPLAY=:1 xwininfo -tree -root

# Wait a bit more and try again
sleep 5
force_window_visibility

# Check if Gateway process is still running
if ps -p $GATEWAY_PID > /dev/null 2>&1; then
    echo "✅ Gateway process is running (PID: $GATEWAY_PID)"
    echo ""
    echo "🎮 Manual Instructions:"
    echo "1. Connect to VNC: vncviewer 35.232.64.211:5901"
    echo "2. Login with: amakua444 / YOUR_IB_PASSWORD"
    echo "3. Configure API: Configuration → API → Enable Socket Clients (port 4002)"
    echo "4. Start trading bot"
    echo ""
    echo "🔧 If window is still not visible, try these xdotool commands:"
    echo "   DISPLAY=:1 xdotool search --name 'Gateway' windowraise"
    echo "   DISPLAY=:1 xdotool search --class 'ibgateway' windowfocus"
else
    echo "❌ Gateway process died"
    exit 1
fi

echo "=========================================="
echo "✅ Gateway startup script completed"
echo "=========================================="