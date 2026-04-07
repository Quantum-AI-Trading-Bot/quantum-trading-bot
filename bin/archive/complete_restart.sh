#!/bin/bash
set -euo pipefail

# ============================================================================
# Complete VNC + IB Gateway Restart Script
# Ensures clean restart of all related processes
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "COMPLETE VNC + IB GATEWAY RESTART"
log "=========================================="

# 1. Stop all VNC processes
log "[1/5] Stopping VNC processes..."
sudo systemctl stop x11vnc.service || true
pkill -f "x11vnc" || true
sleep 3
log "   ✓ VNC processes stopped"

# 2. Stop IB Gateway and IBC processes
log "[2/5] Stopping IB Gateway processes..."
pkill -f "java.*ibgateway" || true
pkill -f "IbcGateway" || true
pkill -f "displaybannerandlaunch.sh" || true
pkill -f "ibcstart.sh" || true
sleep 5
log "   ✓ IB Gateway processes stopped"

# 3. Verify all processes are stopped
log "[3/5] Verifying cleanup..."
REMAINING=$(ps aux | grep -E "(vnc|x11vnc|ibgateway|IbcGateway)" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    log "   ⚠️  Some processes still running, force killing..."
    pkill -9 -f "vnc" || true
    pkill -9 -f "ibgateway" || true
    pkill -9 -f "IBC" || true
    sleep 2
fi
log "   ✓ All processes cleaned up"

# 4. Restart Xvfb (virtual display)
log "[4/5] Restarting virtual display..."
sudo systemctl restart xvfb.service || true
sleep 3
log "   ✓ Virtual display restarted"

# 5. Restart VNC
log "[5/5] Restarting VNC service..."
sudo systemctl start x11vnc.service
sleep 3

# Verify VNC is running
if pgrep -x x11vnc > /dev/null; then
    log "   ✅ VNC service started successfully"
    VNC_PID=$(pgrep -x x11vnc)
    log "   PID: ${VNC_PID}"
else
    log "   ❌ VNC service failed to start"
    exit 1
fi

# Check network connections
log ""
log "Network Status:"
netstat -an | grep 5900 | head -2

log ""
log "=========================================="
log "COMPLETE RESTART FINISHED"
log "=========================================="
log ""
log "VNC Connection Details:"
log "  🖥️  Host: 35.232.64.211"
log "  🔌 Port: 5900"
log "  🔐 Password: (your VNC password)"
log ""
log "Next Steps:"
log "1. Connect with: vncviewer 35.232.64.211:5900"
log "2. Complete IB Gateway authentication manually"
log "3. Test with: /home/davidsanker/platform/bin/test_api_connection.sh"
log "4. Start bot: sudo systemctl start trading-bot.service"
log "=========================================="