#!/bin/bash
echo "🎯 QUANTIM AI TRADING BOT - SYSTEM VERIFICATION"
echo "=================================================="
echo "Time: $(TZ='America/New_York' date)"
echo ""

# Check processes
GATEWAY_COUNT=$(ps aux | grep java | grep ibgateway | grep -v grep | wc -l)
BOT_COUNT=$(pgrep -f "python.*trading_bot" | wc -l)

echo "📊 Process Status:"
echo "   IB Gateway: $GATEWAY_COUNT (should be 1)"
echo "   Trading Bot: $BOT_COUNT (should be 1)"

if [ "$BOT_COUNT" -gt 1 ]; then
    echo "   🚨 TWO-CLIENT CONFLICT DETECTED!"
    echo "   Run: /home/davidsanker/CLIENT_ID_CONFLICT_PERMANENT_SOLUTION.md"
fi

# Check API port
if ss -tlnp | grep -q 4002; then
    echo "   ✅ API Port 4002: Listening"
else
    echo "   ❌ API Port 4002: Not listening"
fi

# Check service
if sudo systemctl is-active --quiet trading-bot.service; then
    echo "   ✅ Service: Active"
else
    echo "   ❌ Service: Inactive"
fi

# Market status
ET_HOUR=$(TZ='America/New_York' date +%H)
if [ "$ET_HOUR" -ge 9 ] && [ "$ET_HOUR" -lt 16 ]; then
    echo "   📈 Market: OPEN (trading active)"
else
    echo "   📴 Market: CLOSED (expect errors)"
fi

echo ""
echo "📋 Quick Commands:"
echo "   Status:     /home/davidsanker/platform/bin/status_dashboard.sh"
echo "   Detection:  /home/davidsanker/platform/bin/two_client_check.sh"
echo "   Restart:    /home/davidsanker/platform/bin/complete_trading_system_start.sh"
echo ""
echo "=================================================="
