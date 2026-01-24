#!/bin/bash
# Trading System Status Dashboard

echo "=================================================="
echo "🚀 QUANTIM AI TRADING BOT - STATUS DASHBOARD"
echo "=================================================="
echo "Time: $(date)"
echo ""

# IB Gateway Status
if pgrep -f "java.*ibgateway" > /dev/null; then
    echo "✅ IB Gateway: RUNNING"
    echo "   PID: $(pgrep -f "java.*ibgateway")"
    if ss -tlnp | grep -q 4002; then
        echo "   API Port: 4002 (Listening)"
        if timeout 5 python3 -c "
from ib_insync import IB; import asyncio
async def test():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=9999, timeout=4)
        print('API_READY')
        ib.disconnect()
    except:
        print('API_FAILED')
asyncio.run(test())
" 2>/dev/null | grep -q "API_READY"; then
            echo "   API Status: CONNECTED"
        else
            echo "   API Status: NOT RESPONDING"
        fi
    else
        echo "   API Port: NOT LISTENING"
    fi
else
    echo "❌ IB Gateway: NOT RUNNING"
fi
echo ""

# Trading Bot Status
BOT_COUNT=$(pgrep -f "python.*trading_bot" | wc -l)
if [ "$BOT_COUNT" -eq 1 ]; then
    echo "✅ Trading Bot: RUNNING"
    echo "   PID: $(pgrep -f "python.*trading_bot")"
elif [ "$BOT_COUNT" -gt 1 ]; then
    echo "⚠️  Trading Bot: MULTIPLE INSTANCES ($BOT_COUNT)"
    echo "   PIDs: $(pgrep -f "python.*trading_bot")"
    echo "   🚨 TWO-CLIENT CONFLICT DETECTED!"
else
    echo "❌ Trading Bot: NOT RUNNING"
fi
echo ""

# System Resources
echo "📊 System Resources:"
echo "   Disk Usage: $(df /home/davidsanker | awk 'NR==2 {print $5}')"
echo "   Memory Usage: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "   Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# Recent Activity
echo "📈 Recent Trading Activity:"
if [ -f "/tmp/trading_bot_active_$(date +%Y%m%d)*.log" ]; then
    tail -3 $(ls -t /tmp/trading_bot_active_$(date +%Y%m%d)*.log | head -1) 2>/dev/null | grep -E "(ORDER|FILL|PRICE)" | tail -3
else
    echo "   No recent activity logs found"
fi
echo ""

echo "=================================================="
