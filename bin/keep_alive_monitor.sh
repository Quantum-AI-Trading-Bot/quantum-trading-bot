#!/bin/bash
# Trading Bot Keep-Alive Monitor
# Runs continuously to ensure the trading bot stays alive

BOT_SCRIPT="/home/davidsanker/investor_bot_migration_20251017_163810/investor/trading_bot.py"
PYTHON_ENV="/home/davidsanker/venv/bin"
LOG_FILE="/tmp/trading_bot_monitor.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_ib_gateway() {
    if ! pgrep -f "java.*ibgateway" > /dev/null; then
        log "❌ IB Gateway is not running - starting it..."
        cd /home/davidsanker && ./platform/bin/start_ib_gateway.sh &
        sleep 30
    fi

    # Check API connectivity
    if ! timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    print('API_READY')
    ib.disconnect()
except:
    print('API_DOWN')
" 2>/dev/null | grep -q "API_READY"; then
        log "⚠️ IB Gateway API not ready - attempting auto-login..."
        ./platform/bin/auto_login_gui.sh
    fi
}

check_trading_bot() {
    BOT_COUNT=$(pgrep -f "python.*trading_bot" | wc -l)

    if [ "$BOT_COUNT" -eq 0 ]; then
        log "❌ Trading bot is not running - starting it..."
        cd /home/davidsanker/investor_bot_migration_20251017_163810/investor
        source /home/davidsanker/venv/bin/activate
        nohup python trading_bot.py > /tmp/trading_bot_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &
        sleep 10
    elif [ "$BOT_COUNT" -gt 1 ]; then
        log "⚠️ Multiple trading bot instances detected - cleaning up..."
        pgrep -f "python.*trading_bot" | tail -n +2 | xargs kill
    fi
}

# Main monitoring loop
log "🚀 Trading Bot Keep-Alive Monitor Started"
while true; do
    check_ib_gateway
    check_trading_bot

    # Log status
    GATEWAY_STATUS=$(pgrep -f "java.*ibgateway" > /dev/null && echo "RUNNING" || echo "DOWN")
    BOT_STATUS=$(pgrep -f "python.*trading_bot" > /dev/null && echo "RUNNING" || echo "DOWN")
    log "✅ Status Check - IB Gateway: $GATEWAY_STATUS | Trading Bot: $BOT_STATUS"

    sleep 60  # Check every minute
done