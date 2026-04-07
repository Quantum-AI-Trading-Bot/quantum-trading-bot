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
