##############################################################################
# DEPRECATED - DO NOT USE
##############################################################################
# This script has been quarantined due to security concerns.
# It may contain hardcoded credentials or use unsafe automation practices.
# 
# Migration path:
# - Use VNC/noVNC for manual IB Gateway login
# - Use IBC (Interactive Brokers Controller) for automated startup
# - Monitor IB Gateway health via watchdog_ib_gateway.sh
#
# Manual login via VNC:
#   vncviewer 35.232.64.211:5901
#   or http://35.232.64.211:6080/vnc.html
##############################################################################

#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "🌅 Daily IB Gateway Authentication Window"

# Ensure IB Gateway is running
if ! pgrep -f "java.*ibgateway" > /dev/null; then
    log "Starting IB Gateway..."
    export DISPLAY=:1
    cd /home/davidsanker
    nohup /home/davidsanker/IBGateway/ibgateway.bin > /tmp/daily_gateway.log 2>&1 &
    sleep 45
fi

# Run GUI automation
log "Running GUI automation for login..."
/home/davidsanker/platform/bin/auto_login_gui.sh

log "✅ Daily authentication setup complete"
log "💡 Reminder: Complete 2FA on your mobile device within 3 minutes"
