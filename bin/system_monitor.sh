#!/bin/bash
# 24/7 System Health Monitor

LOG_DIR="/home/davidsanker/platform/logs/monitoring"
LOG_FILE="${LOG_DIR}/health_$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

check_ib_gateway() {
    if ! pgrep -f "java.*ibgateway" > /dev/null; then
        log "❌ IB Gateway not running - starting fresh..."
        /home/davidsanker/platform/bin/complete_trading_system_start.sh &
        return 1
    fi
    return 0
}

check_trading_bot() {
    if ! pgrep -f "python.*trading_bot" > /dev/null; then
        log "❌ Trading Bot not running - restarting..."
        cd /home/davidsanker/investor_bot_migration_20251017_163810/investor
        source /home/davidsanker/venv/bin/activate
        nohup python trading_bot.py >> /home/davidsanker/platform/logs/trading-bot/auto_restart.log 2>&1 &
        return 1
    fi
    return 0
}

check_api_connection() {
    if ! timeout 10 python3 -c "
from ib_insync import IB; import asyncio
async def test():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=9999, timeout=6)
        ib.disconnect()
    except:
        exit(1)
asyncio.run(test())
" 2>/dev/null; then
        log "❌ API not responding - restarting system..."
        /home/davidsanker/platform/bin/complete_trading_system_start.sh &
        return 1
    fi
    return 0
}

check_disk_space() {
    USAGE=$(df /home/davidsanker | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 80 ]; then
        log "⚠️  Disk usage high: ${USAGE}%"
        # Clean old logs
        find /home/davidsanker/platform/logs -name "*.log" -mtime +3 -delete
    fi
}

# Run all checks
ISSUES=0
check_ib_gateway || ISSUES=$((ISSUES + 1))
check_trading_bot || ISSUES=$((ISSUES + 1))
check_api_connection || ISSUES=$((ISSUES + 1))
check_disk_space

if [ $ISSUES -eq 0 ]; then
    log "✅ All systems operational"
fi
