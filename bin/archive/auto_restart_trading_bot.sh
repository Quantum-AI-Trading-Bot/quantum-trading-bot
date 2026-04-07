#!/bin/bash
# Auto-Restart Trading Bot with Reconnection Management

set -euo pipefail

LOG_DIR="/home/davidsanker/platform/logs/trading-bot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/auto_restart_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Function to test IB Gateway API connection
test_api_connection() {
    source /home/davidsanker/venv/bin/activate
    timeout 8 python3 -c "
from ib_insync import IB
import asyncio

async def test():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=9999, timeout=6)
        print('API_SUCCESS')
        ib.disconnect()
        return True
    except Exception as e:
        return False

result = asyncio.run(test())
print('API_SUCCESS' if result else 'API_FAILED')
" 2>/dev/null | grep -q "API_SUCCESS"
}

# Function to start trading bot with unique client ID
start_trading_bot() {
    local client_id=$1
    log "Starting trading bot with client ID: ${client_id}"

    cd /home/davidsanker/investor_bot_migration_20251017_163810/investor
    source /home/davidsanker/venv/bin/activate

    # Use simple trading bot first
    nohup python3 -c "
import sys
import os
sys.path.insert(0, '.')

# Import and modify the trading bot to use our client ID
import trading_bot
trading_bot.CLIENT_ID = ${client_id}
trading_bot.IB_HOST = '127.0.0.1'
trading_bot.IB_PORT = 4002

# Start the bot
trading_bot.main()
" > "${LOG_DIR}/trading_bot_${client_id}_${TIMESTAMP}.log" 2>&1 &

    echo $!
}

# Main execution
log "=========================================="
log "AUTO-RESTART TRADING BOT MANAGER"
log "=========================================="

# Test API connection first
if ! test_api_connection; then
    log "❌ IB Gateway API not ready. Please ensure Gateway is running and API is configured."
    exit 1
fi

log "✅ IB Gateway API is ready"

# Kill any existing trading bot processes
pkill -f "python.*trading_bot" || true
sleep 3

# Start trading bot with unique client ID
CLIENT_ID=1001  # Start with 1001 to avoid conflicts
BOT_PID=$(start_trading_bot $CLIENT_ID)

log "✅ Trading bot started (PID: ${BOT_PID}, Client ID: ${CLIENT_ID})"
log "📊 Monitoring log: ${LOG_DIR}/trading_bot_${CLIENT_ID}_${TIMESTAMP}.log"
log "🔄 Auto-restart functionality: ACTIVE (will restart on disconnect)"

# Keep the script running to monitor
while true; do
    sleep 300  # Check every 5 minutes

    # Check if bot is still running
    if ! kill -0 $BOT_PID 2>/dev/null; then
        log "⚠️  Trading bot stopped, attempting restart..."

        # Test API connection
        if test_api_connection; then
            CLIENT_ID=$((CLIENT_ID + 1))
            BOT_PID=$(start_trading_bot $CLIENT_ID)
            log "🔄 Trading bot restarted (PID: ${BOT_PID}, Client ID: ${CLIENT_ID})"
        else
            log "❌ IB Gateway API not available, will retry later..."
        fi
    fi

    # Test API connectivity periodically
    if ! test_api_connection; then
        log "⚠️  API connection lost, preparing to restart bot..."
        kill $BOT_PID 2>/dev/null || true
        sleep 10

        if test_api_connection; then
            CLIENT_ID=$((CLIENT_ID + 1))
            BOT_PID=$(start_trading_bot $CLIENT_ID)
            log "🔄 Trading bot restarted due to API reconnect (Client ID: ${CLIENT_ID})"
        fi
    fi
done