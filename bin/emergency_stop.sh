#!/bin/bash
set -euo pipefail

# ============================================================================
# Emergency Stop - Safe Shutdown with Position Closing
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "EMERGENCY STOP INITIATED"
log "=========================================="

# 1. Stop trading bot gracefully (sends SIGTERM, allows position closing)
log "[1/3] Stopping trading bot gracefully..."
if pgrep -f "quantum_enhanced_trading_bot.py" > /dev/null; then
    BOT_PID=$(pgrep -f "quantum_enhanced_trading_bot.py")
    log "   Sending SIGTERM to bot (PID: ${BOT_PID})"
    kill -TERM ${BOT_PID}

    # Wait up to 60 seconds for graceful shutdown
    for i in {1..12}; do
        if ! pgrep -f "quantum_enhanced_trading_bot.py" > /dev/null; then
            log "   ✓ Bot stopped gracefully"
            break
        fi
        sleep 5
    done

    # Force kill if still running
    if pgrep -f "quantum_enhanced_trading_bot.py" > /dev/null; then
        log "   ⚠ Bot did not stop gracefully, force killing..."
        pkill -9 -f "quantum_enhanced_trading_bot.py"
    fi
else
    log "   (Bot not running)"
fi

# 2. Stop IB Gateway
log "[2/3] Stopping IB Gateway..."
if pgrep -f "java.*ibgateway" > /dev/null; then
    pkill -f "java.*ibgateway"
    sleep 5
    log "   ✓ Gateway stopped"
else
    log "   (Gateway not running)"
fi

# 3. Stop systemd services
log "[3/3] Stopping systemd services..."
sudo systemctl stop trading-bot.service || true
sudo systemctl stop ib-gateway.service || true
log "   ✓ Services stopped"

log "=========================================="
log "EMERGENCY STOP COMPLETE"
log "=========================================="
