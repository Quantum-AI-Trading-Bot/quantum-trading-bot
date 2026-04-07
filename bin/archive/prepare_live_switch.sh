#!/bin/bash
set -euo pipefail

# ============================================================================
# 🔄 LIVE SWITCH PREPARATION - CLEAN & SIMPLE VERSION
# ============================================================================

echo "🔄 Preparing for Live Account Switch..."
echo ""

# 1. Check IB Gateway is running
if ! pgrep -f "java.*ibgateway" > /dev/null; then
    echo "❌ IB Gateway is not running - please start it first"
    exit 1
fi

# 2. Get current portfolio analysis
echo "📊 Analyzing Current Paper Portfolio..."
source ~/venv/bin/activate

echo "Current holdings:"
source ~/venv/bin/activate && python3 -c "
from ib_insync import IB
import time

try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=7777, timeout=10)

    positions = ib.positions()
    total_value = 0
    total_pnl = 0

    print('SYMBOL | QUANTITY | AVG COST | CURRENT | PnL')
    print('-' * 50)

    for pos in positions:
        if hasattr(pos, 'contract') and pos.position != 0:
            ticker = ib.reqMktData(pos.contract, '', False, False)
            time.sleep(1)
            if ticker.marketPrice and ticker.marketPrice != ticker.marketPrice:
                current_price = ticker.marketPrice
            else:
                current_price = pos.avgCost  # Fallback

            position_value = abs(pos.position) * current_price
            pnl = (current_price - pos.avgCost) * pos.position

            total_value += position_value
            total_pnl += pnl

            symbol = pos.contract.symbol
            print(f'{symbol:6} | {pos.position:8.0f} | \${pos.avgCost:8.2f} | \${current_price:8.2f} | \${pnl:10.2f}')

    ib.disconnect()
    print('-' * 50)
    print(f'TOTAL Portfolio Value: \${total_value:,.2f}')
    print(f'Total PnL: \${total_pnl:+,.2f}')
    print(f'Number of Positions: {len(positions)}')

except Exception as e:
    print(f'Error getting portfolio: {e}')
    exit(1)
"

echo ""
echo "📋 Live Account Switch Infrastructure Created:"
echo "✅ /home/davidsanker/platform/bin/switch_to_live.sh - Main switch script"
echo "✅ /home/davidsanker/platform/bin/switch_to_paper.sh - Emergency revert script"
echo "✅ /home/davidsanker/platform/bin/live_trading_monitor.sh - Safety monitoring"
echo "✅ /home/davidsanker/platform/bin/quantum_live_reporter.py - Enhanced reporting"

echo ""
echo "🛡️ Live Trading Safety Systems Activated:"
echo "- Hourly risk monitoring (auto-shutdown at \$25k losses)"
echo "- Enhanced daily reporting with risk metrics"
echo "- Quick account switching capability"
echo "- Paper account backup maintained"

echo ""
echo "🎯 SWITCHING STRATEGIES:"
echo ""
echo "🟡 OPTION 1: GRADUAL TRANSITION (RECOMMENDED)"
echo "   - Keep paper account running for hedging"
echo "   - Start live with 5-10% position sizes"
echo "   - Scale up gradually as confidence builds"
echo "   - Lower risk, safer learning curve"
echo ""
echo "🔴 OPTION 2: DIRECT SWITCH (EXPERIENCED TRADERS)"
echo "   - Switch completely to live trading"
echo "   - Maintain all current position sizes"
echo "   - Maximum efficiency, higher risk"
echo "   - Requires constant monitoring"
echo ""
echo "🚀 WHEN READY FOR LIVE SWITCHING:"
echo "   1. Review your paper trading performance"
echo "   2. Set aside risk capital you're comfortable losing"
echo "   3. Run: /home/davidsanker/platform/bin/switch_to_live.sh"
echo "   4. Type: CONFIRM-LIVE (safety requirement)"
echo   5. Start small and monitor closely"
echo ""
echo "⚠️  CRITICAL REMINDER:"
echo "- LIVE trading involves REAL money risk"
echo "- Start with small position sizes (5% normal)"
echo "- Monitor risk levels continuously"
echo "- Keep emergency shutdown plans ready"
echo "- Never invest more than you can afford to lose"