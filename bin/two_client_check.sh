#!/bin/bash
# Two-Client Conflict Detection Script
# Early warning system for multiple trading bot instances

echo "🔍 TWO-CLIENT CONFLICT DETECTION"
echo "==============================="
echo "Time: $(date)"
echo ""

# Count processes
GATEWAY_COUNT=$(ps aux | grep java | grep ibgateway | grep -v grep | wc -l)
BOT_COUNT=$(pgrep -f "python.*trading_bot" | wc -l)

echo "📊 Process Counts:"
echo "   IB Gateway: $GATEWAY_COUNT"
echo "   Trading Bot: $BOT_COUNT"
echo ""

# Detection logic
if [ "$GATEWAY_COUNT" -gt 1 ]; then
    echo "🚨 MULTIPLE GATEWAY INSTANCES DETECTED!"
    echo "   PIDs: $(ps aux | grep java | grep ibgateway | grep -v grep | awk '{print $2}')"
    echo ""
fi

if [ "$BOT_COUNT" -gt 1 ]; then
    echo "🚨 TWO-CLIENT CONFLICT DETECTED!"
    echo "   Multiple trading bot instances running"
    echo "   PIDs: $(pgrep -f "python.*trading_bot")"
    echo ""
    echo "🛠️  IMMEDIATE FIX REQUIRED:"
    echo "   Run: /home/davidsanker/CLIENT_ID_CONFLICT_PERMANENT_SOLUTION.md"
    echo ""
elif [ "$BOT_COUNT" -eq 1 ]; then
    echo "✅ Single trading bot instance - OK"
elif [ "$BOT_COUNT" -eq 0 ]; then
    echo "❌ No trading bot running"
fi

# Check API port
if ss -tlnp | grep -q 4002; then
    echo "✅ API port 4002 listening"
else
    echo "❌ API port 4002 not listening"
fi

echo ""
echo "==============================="