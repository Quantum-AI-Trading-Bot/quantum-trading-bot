#!/bin/bash
set -euo pipefail

# ============================================================================
# IB Gateway Connection Fix Script
# Addresses the common IB Gateway API connection issues
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/fix_gateway_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

die() {
    log "ERROR: $*"
    exit 1
}

log "=========================================="
log "IB GATEWAY CONNECTION FIX"
log "=========================================="

# 1. Check virtual environment and dependencies
log "[1/8] Checking Python environment..."
if [ ! -d ~/venv ]; then
    log "Creating virtual environment..."
    python3 -m venv ~/venv
fi

source ~/venv/bin/activate

# Install required packages if missing
log "Installing/updating required packages..."
pip install --quiet ib_insync pandas numpy qiskit torch || log "WARNING: Some packages failed to install"

log "   ✓ Python environment OK"

# 2. Test basic API connectivity
log "[2/8] Testing IB Gateway API connectivity..."

# Try multiple times - IB Gateway can be slow to initialize
API_CONNECTED=false
for i in {1..5}; do
    log "   Attempt ${i}/5..."

    if timeout 15 python3 -c "
from ib_insync import IB
import sys
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=998, timeout=10)
    accounts = ib.managedAccounts()
    print(f'Connected successfully. Account: {accounts[0] if accounts else \"None\"}')
    ib.disconnect()
    print('API_TEST_SUCCESS')
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "API_TEST_SUCCESS"; then
        API_CONNECTED=true
        log "   ✓ API connection successful!"
        break
    else
        log "   ⏳ API not ready, waiting 10 seconds..."
        sleep 10
    fi
done

if [ "$API_CONNECTED" = false ]; then
    log "   ❌ API connection failed after 5 attempts"
    log "   This indicates a deeper issue with the Gateway"
fi

# 3. Check if Gateway is properly configured
log "[3/8] Validating Gateway configuration..."

# Check if API is enabled in Gateway
if timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=997, timeout=5)
    # Test a simple operation
    ib.reqCurrentTime()
    print('Gateway configured correctly')
    ib.disconnect()
except Exception as e:
    print(f'Gateway config issue: {e}')
    exit(1)
" 2>/dev/null; then
    log "   ✓ Gateway configuration OK"
else
    log "   ⚠️  Gateway may have configuration issues"
fi

# 4. Manual authentication guidance
log "[4/8] Authentication check..."
log "   If you haven't authenticated today, you need to:"
log "   1. Open VNC to see the Gateway screen"
log "   2. Complete 2FA if prompted"
log "   3. Ensure 'Active Trading' is enabled"

# 5. Restart Gateway if needed
log "[5/8] Checking Gateway restart status..."

if [ "$API_CONNECTED" = false ]; then
    log "   API not connected, attempting Gateway restart..."

    # Stop current Gateway
    if pgrep -f "java.*ibgateway" > /dev/null; then
        log "   Stopping current Gateway..."
        pkill -f "java.*ibgateway"
        sleep 10
    fi

    # Start Gateway with IBC
    log "   Starting Gateway with IBC..."
    cd /home/davidsanker/IBC
    nohup java -cp IBC.jar ibcalpha.ibc.IbcGateway /home/davidsanker/IBC/config.ini paper > "${LOG_DIR}/restart_${TIMESTAMP}.log" 2>&1 &

    # Wait for startup
    log "   Waiting for Gateway startup (this can take 60-90 seconds)..."
    sleep 60

    # Test again
    if timeout 15 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=10)
    print('RESTART_SUCCESS')
    ib.disconnect()
except:
    exit(1)
" 2>/dev/null | grep -q "RESTART_SUCCESS"; then
        log "   ✓ Gateway restart successful!"
        API_CONNECTED=true
    else
        log "   ❌ Gateway restart did not resolve the issue"
    fi
fi

# 6. Final connectivity test
log "[6/8] Final comprehensive connectivity test..."

if [ "$API_CONNECTED" = true ]; then
    log "   Testing advanced API operations..."
    timeout 15 python3 -c "
from ib_insync import IB, Stock, util
util.startLoop()
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1000, timeout=10)

    # Test account info
    accounts = ib.managedAccounts()
    print(f'✓ Accounts: {accounts}')

    # Test market data (for paper trading)
    contract = Stock('AAPL', 'SMART', 'USD')
    ib.qualifyContracts(contract)
    print('✓ Contract qualification works')

    # Test basic data request
    ticker = ib.reqMktData(contract, '', False, False)
    ib.sleep(2)
    if ticker.hasBidAsk:
        print(f'✓ Market data: Bid={ticker.bid}, Ask={ticker.ask}')

    ib.disconnect()
    print('ADVANCED_TEST_SUCCESS')
except Exception as e:
    print(f'Advanced test failed: {e}')
    exit(1)
" 2>/dev/null | grep -q "ADVANCED_TEST_SUCCESS"

    if [ $? -eq 0 ]; then
        log "   ✓ All API functions working correctly!"
    else
        log "   ⚠️  Basic connection works, but some features may be limited"
    fi
fi

# 7. Trading bot specific tests
log "[7/8] Testing trading bot requirements..."

if [ "$API_CONNECTED" = true ]; then
    timeout 15 python3 -c "
from ib_insync import IB
import pandas as pd
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1001, timeout=10)

    # Test the operations your trading bot uses
    accounts = ib.managedAccounts()
    account = accounts[0] if accounts else None

    if account:
        # Test account summary
        summary = ib.accountSummary(account)
        print(f'✓ Account summary: {len(summary)} items')

        # Test portfolio positions
        positions = ib.positions(account)
        print(f'✓ Positions: {len(positions)}')

    ib.disconnect()
    print('BOT_REQUIREMENTS_OK')
except Exception as e:
    print(f'Bot requirements test failed: {e}')
    exit(1)
" 2>/dev/null | grep -q "BOT_REQUIREMENTS_OK"

    if [ $? -eq 0 ]; then
        log "   ✓ Trading bot requirements satisfied!"
    else
        log "   ⚠️  Some trading bot features may not work"
    fi
fi

# 8. Recommendations
log "[8/8] Generating recommendations..."

log ""
log "=========================================="
log "RECOMMENDATIONS"
log "=========================================="

if [ "$API_CONNECTED" = true ]; then
    log "✅ IB Gateway is working correctly!"
    log ""
    log "Next steps:"
    log "1. Start the trading bot:"
    log "   sudo systemctl start trading-bot.service"
    log ""
    log "2. Monitor the logs:"
    log "   tail -f /home/davidsanker/platform/logs/trading-bot/*.log"
    log ""
    log "3. Set up automated restarts:"
    log "   # Add to crontab for daily restarts at 11 PM"
    log "   0 23 * * * /home/davidsanker/platform/bin/start_ib_gateway.sh"
else
    log "❌ IB Gateway connection issues detected"
    log ""
    log "Immediate actions needed:"
    log "1. Manual Authentication:"
    log "   - Open VNC connection: vnc://localhost:5901"
    log "   - Complete 2FA if prompted"
    log "   - Ensure Gateway shows 'Active trading enabled'"
    log ""
    log "2. Configuration Check:"
    log "   - Verify paper trading account credentials"
    log "   - Check API is enabled in Gateway settings"
    log "   - Confirm port 4002 is not blocked"
    log ""
    log "3. Alternative solutions:"
    log "   - Try TWS instead of Gateway (more reliable)"
    log "   - Contact IB support if issues persist"
    log "   - Consider running on a different machine/port"
fi

log ""
log "=========================================="
log "Fix script complete. Log saved to: ${LOG_FILE}"
log "=========================================="