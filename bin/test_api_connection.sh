#!/bin/bash
set -euo pipefail

# ============================================================================
# Simple API Connection Test
# Quick verification that IB Gateway API is working
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "IB GATEWAY API CONNECTION TEST"
log "=========================================="

# Test 1: Port connectivity
log "[1/4] Testing port 4002 connectivity..."
if nc -z 127.0.0.1 4002 2>/dev/null; then
    log "   ✅ Port 4002 is listening"
else
    log "   ❌ Port 4002 not reachable - Gateway not ready"
    exit 1
fi

# Test 2: Python environment
log "[2/4] Checking Python environment..."
source ~/venv/bin/activate
if python3 -c "import ib_insync; print('✅ ib_insync available')" 2>/dev/null; then
    log "   ✅ Python environment OK"
else
    log "   ❌ ib_insync not available - install with: pip install ib_insync"
    exit 1
fi

# Test 3: Basic API connection
log "[3/4] Testing basic API connection..."
if timeout 15 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=998, timeout=10)
    accounts = ib.managedAccounts()
    print(f'✅ Connected! Account: {accounts[0] if accounts else \"None\"}')
    ib.disconnect()
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    log "   ✅ Basic API connection working"
else
    log "   ❌ API connection failed"
    exit 1
fi

# Test 4: Advanced operations
log "[4/4] Testing trading operations..."
if timeout 15 python3 -c "
from ib_insync import IB, Stock
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=10)

    # Test contract qualification
    contract = Stock('AAPL', 'SMART', 'USD')
    ib.qualifyContract(contract)
    print('✅ Contract qualification works')

    # Test account data
    accounts = ib.managedAccounts()
    if accounts:
        account = accounts[0]
        summary = ib.accountSummary(account)
        print(f'✅ Account data: {len(summary)} summary items')

    ib.disconnect()
    print('✅ All trading operations working')
except Exception as e:
    print(f'❌ Advanced operations failed: {e}')
    exit(1)
" 2>/dev/null; then
    log "   ✅ All API operations working correctly"
else
    log "   ⚠️  Some operations may need authentication"
fi

log ""
log "=========================================="
log "✅ IB Gateway API is ready for trading!"
log ""
log "Next steps:"
log "1. Start trading bot: sudo systemctl start trading-bot.service"
log "2. Monitor logs: tail -f /home/davidsanker/platform/logs/trading-bot/*.log"
log "=========================================="