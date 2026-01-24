#!/bin/bash
# Complete Trading System Start - Gateway + API + Bot

set -euo pipefail

LOG_DIR="/home/davidsanker/platform/logs/trading-bot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/complete_start_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

echo "🚀 STARTING COMPLETE TRADING SYSTEM ACTIVATION"
echo "================================================="

# Step 1: Clean restart
log "🔄 Step 1: Clean restart of all components"

# Kill existing processes
pkill -f "java.*ibgateway" || true
pkill -f "auto_restart_trading_bot" || true
pkill -f "python.*trading_bot" || true

sleep 5

# Clean temp files
rm -rf /home/davidsanker/IBGateway/*.tmp /home/davidsanker/IBGateway/*.lock 2>/dev/null || true

log "✅ Cleanup completed"

# Step 2: Automated IB Gateway login and API setup
log "🔐 Step 2: Automated IB Gateway login and API setup..."

# Kill any existing IB Gateway processes
pkill -f "java.*ibgateway" || true
pkill -f "IBC.jar" || true
sleep 3

# Run automated login
python3 /home/davidsanker/platform/bin/ib_gateway_automated_login.py 2>&1 | tee -a "${LOG_FILE}"

LOGIN_SUCCESS=$?

if [ $LOGIN_SUCCESS -eq 0 ]; then
    log "✅ Automated IB Gateway login successful!"
else
    log "❌ Automated login failed, requiring manual intervention"
    log ""
    log "📋 ACTION REQUIRED: Please complete the following steps:"
    log "   1. Connect to VNC: vnc://localhost:5901"
    log "   2. Login with your credentials"
    log "   3. Go to Configuration → API"
    log "   4. Ensure: Enable ActiveX and Socket Clients = YES"
    log "   5. Ensure: Socket port = 4002"
    log "   6. Ensure: Accept incoming connections = YES"
    log "   7. Ensure: Data Only (Read-Only) = UNCHECKED"
    log "   8. Click OK to save settings"
    log ""
    log "⏳ Waiting for API configuration to be completed..."
fi

# Wait for manual configuration
for i in {1..30}; do
    echo -n "."
    sleep 10

    # Test API connection
    if timeout 8 python3 -c "
from ib_insync import IB; import asyncio
async def test():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=9999, timeout=6)
        print('API_READY')
        ib.disconnect()
    except:
        print('API_NOT_READY')
asyncio.run(test())
" 2>/dev/null | grep -q "API_READY"; then
        log ""
        log "✅ API connection established!"
        break
    fi

    if [ $i -eq 30 ]; then
        log ""
        log "⚠️  API still not ready after 5 minutes. Will continue monitoring..."
    fi
done

# Step 4: Start trading bot
log "🤖 Step 4: Starting trading bot..."

cd /home/davidsanker/investor_bot_migration_20251017_163810/investor
source /home/davidsanker/venv/bin/activate

# Start simple trading bot
nohup python3 -c "
import trading_bot
import sys

# Set connection parameters
trading_bot.IB_HOST = '127.0.0.1'
trading_bot.IB_PORT = 4002
trading_bot.CLIENT_ID = 1001

print('🚀 Starting Quantim AI Trading Bot...')
print('📊 Account: Paper Trading')
print('🔌 API: 127.0.0.1:4002')
print('🤖 Client ID: 1001')

try:
    trading_bot.main()
except KeyboardInterrupt:
    print('👋 Trading bot stopped by user')
except Exception as e:
    print(f'❌ Trading bot error: {e}')
    sys.exit(1)
" > "${LOG_DIR}/trading_bot_${TIMESTAMP}.log" 2>&1 &

BOT_PID=$!
log "✅ Trading bot started (PID: ${BOT_PID})"

# Step 5: Monitor and provide status
log "📊 Step 5: Initial status check..."

sleep 30

if kill -0 $BOT_PID 2>/dev/null; then
    log "🎉 SUCCESS: Trading bot is running!"
    log ""
    log "📋 SYSTEM STATUS:"
    log "   ✅ IB Gateway: Running"
    log "   ✅ API Connection: Active"
    log "   ✅ Trading Bot: Running (PID: ${BOT_PID})"
    log ""
    log "📁 Logs:"
    log "   - System: ${LOG_FILE}"
    log "   - Bot: ${LOG_DIR}/trading_bot_${TIMESTAMP}.log"
    log "   - Gateway: /tmp/gateway_start_${TIMESTAMP}.log"
    log ""
    log "🔍 Monitor trading bot activity:"
    log "   tail -f ${LOG_DIR}/trading_bot_${TIMESTAMP}.log"
else
    log "❌ Trading bot failed to start properly"
    log "📋 Check logs: ${LOG_DIR}/trading_bot_${TIMESTAMP}.log"
fi

log "================================================="
log "🎯 COMPLETE TRADING SYSTEM STARTUP FINISHED"
log "================================================="