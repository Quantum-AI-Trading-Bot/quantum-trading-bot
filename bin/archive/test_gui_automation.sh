#!/bin/bash
set -e

# Test GUI automation for IB Gateway login

export DISPLAY=:1

echo "=== Testing IB Gateway GUI Automation ==="

# Find the Gateway window
WINDOW_ID=$(xdotool search --class "Gateway" | head -1)
if [ -z "$WINDOW_ID" ]; then
    echo "❌ IB Gateway window not found"
    exit 1
fi

echo "✅ Found IB Gateway window: $WINDOW_ID"

# Activate the window
echo "Activating IB Gateway window..."
xdotool windowactivate "$WINDOW_ID"

# Wait a moment for activation
sleep 2

# Try to take a screenshot to see what's displayed
echo "Taking screenshot for verification..."
DISPLAY=:1 import -window "$WINDOW_ID" /tmp/gateway_screenshot.png 2>/dev/null || echo "Screenshot failed (ImageMagick not available)"

# Try to find username field
echo "Looking for username field..."
# This is experimental - may need adjustment based on actual UI

# Test basic GUI interaction
echo "Testing basic GUI interaction..."
xdotool key Tab
sleep 1
xdotool key Tab
sleep 1
xdotool key Shift+Tab
sleep 1

echo "✅ GUI automation test completed"
echo "The Gateway window should be active and ready for manual credential input"
echo "You can now connect via VNC (localhost:5901) to complete the login"