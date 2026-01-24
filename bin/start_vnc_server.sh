#!/bin/bash
set -e

echo "🖥️ Starting VNC Server with Proper Configuration"
echo "=============================================="

LOG_FILE="/home/davidsanker/logs/vnc_startup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Clean up any existing VNC/X11 processes
log "🧹 Cleaning up existing VNC/X11 processes..."
pkill -f "Xvnc" 2>/dev/null || true
pkill -f "x11vnc" 2>/dev/null || true
pkill -f "Xnest" 2>/dev/null || true
sleep 2

# Set up DISPLAY environment
export DISPLAY=:1

# Start X server if not running
log "🚀 Starting X server..."
if ! xdpyinfo -display :1 >/dev/null 2>&1; then
    # Use Xvfb (virtual framebuffer) for headless operation
    Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset 2>/dev/null &
    XVFB_PID=$!
    sleep 3

    # Verify X server is running
    if xdpyinfo -display :1 >/dev/null 2>&1; then
        log "✅ X server started successfully (PID: $XVFB_PID)"
    else
        log "❌ Failed to start X server"
        exit 1
    fi
else
    log "✅ X server already running"
fi

# Set window manager
log "🪟 Starting window manager..."
export XDG_CONFIG_HOME=/tmp
export XDG_DATA_HOME=/tmp

# Start a simple window manager
metacity --replace --display :1 2>/dev/null &
WM_PID=$!
sleep 2

# Start VNC server
log "🌐 Starting VNC server..."
x11vnc -display :1 -forever -nopw -quiet -bg -shared -rfbport 5901 \
    -ncache 10 -ncache_cr -waitms 1000 -defer 5 2>/dev/null &
VNC_PID=$!

sleep 3

# Verify VNC server is running
if netstat -tuln | grep -q ":5901 "; then
    log "✅ VNC server started successfully on localhost:5901"
    log ""
    log "📋 VNC Connection Details:"
    log "   URL: vnc://localhost:5901"
    log "   Display: :1"
    log "   Resolution: 1920x1080"
    log ""
    log "🖥️ Desktop Environment: Ready"
    log "📱 VNC is ready for connections"
    log ""
    log "🔍 To verify VNC is working:"
    log "   vncviewer localhost:5901"
    log "   # or"
    log "   DISPLAY=:1 xclock  # Should show a clock"

    # Test with a simple application
    export DISPLAY=:1
    if command -v xclock >/dev/null 2>&1; then
        xclock >/dev/null 2>&1 &
        log "✅ Test application (xclock) started"
    fi

    log ""
    log "✅ VNC server is ready for IB Gateway!"

else
    log "❌ VNC server failed to start on port 5901"
    exit 1
fi

# Save PIDs for cleanup
echo "$XVFB_PID" > /tmp/vnc_xvfb.pid
echo "$WM_PID" > /tmp/vnc_wm.pid
echo "$VNC_PID" > /tmp/vnc_server.pid

log "📝 Process IDs saved for cleanup"
log "🎉 VNC server setup complete!"