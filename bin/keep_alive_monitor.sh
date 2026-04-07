#!/bin/bash
# Trading Bot Keep-Alive Monitor
# Runs continuously to ensure the trading bot stays alive

BOT_SCRIPT="/home/davidsanker/platform/bin/quantum_enhanced_trading_bot.py"
PYTHON_ENV="/home/davidsanker/venv/bin"
LOG_FILE="/tmp/trading_bot_monitor.log"

# Ensure DISPLAY is set for IB Gateway (Xvfb runs on :1)
export DISPLAY="${DISPLAY:-:1}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_ib_gateway() {
    # If gateway process is already running, don't start another
    if pgrep -f "IbcGateway" > /dev/null; then
        # Process exists — only check if port is open (lightweight)
        if ! nc -z 127.0.0.1 4002 2>/dev/null; then
            log "⚠️ IB Gateway process running but port 4002 not open yet - waiting"
        fi
        return 0
    fi

    # Gateway is truly not running — start it (foreground, wait for completion)
    log "❌ IB Gateway is not running - starting it..."
    cd /home/davidsanker && ./platform/bin/start_ib_gateway.sh || true
}

check_trading_bot() {
    BOT_COUNT=$(pgrep -f "python.*quantum_enhanced_trading_bot" | wc -l)

    if [ "$BOT_COUNT" -eq 0 ]; then
        log "❌ Trading bot is not running - starting it..."
        cd /home/davidsanker
        source /home/davidsanker/venv/bin/activate
        nohup python "$BOT_SCRIPT" > /tmp/trading_bot_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &
        sleep 10
    elif [ "$BOT_COUNT" -gt 1 ]; then
        log "⚠️ Multiple trading bot instances detected - cleaning up..."
        pgrep -f "python.*quantum_enhanced_trading_bot" | tail -n +2 | xargs kill
    fi
}

# Main monitoring loop
log "🚀 Trading Bot Keep-Alive Monitor Started"
while true; do
    check_ib_gateway
    check_trading_bot

    # Log status
    GATEWAY_STATUS=$(pgrep -f "IbcGateway" > /dev/null && echo "RUNNING" || echo "DOWN")
    BOT_STATUS=$(pgrep -f "python.*quantum_enhanced_trading_bot" > /dev/null && echo "RUNNING" || echo "DOWN")
    log "✅ Status Check - IB Gateway: $GATEWAY_STATUS | Trading Bot: $BOT_STATUS"

    sleep 60  # Check every minute
done