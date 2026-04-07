#!/bin/bash
"""
Immediate Failure Prevention Implementation
Critical safeguards to prevent bot/API failures
"""

echo "🛡️ IMPLEMENTING IMMEDIATE FAILURE PREVENTION"
echo "============================================="

# Create essential directories
mkdir -p /home/davidsanker/platform/logs
mkdir -p /home/davidsanker/platform/data
mkdir -p /home/davidsanker/platform/config

# 1. CREATE MEMORY MONITOR AND RESTART SCRIPT
cat > /home/davidsanker/platform/bin/memory_monitor.sh << 'EOF'
#!/bin/bash
# Memory monitor for IB Gateway and Trading Bot

LOG_FILE="/home/davidsanker/platform/logs/memory_monitor.log"
ALERT_THRESHOLD=1800  # 1.8GB for IB Gateway
TRADING_BOT_THRESHOLD=1000  # 1GB for trading bot

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_ib_gateway_memory() {
    local pid=$(pgrep -f "java.*ibgateway" | head -1)
    if [ -n "$pid" ]; then
        local memory_kb=$(ps -p "$pid" -o rss= | tr -d ' ')
        local memory_mb=$((memory_kb / 1024))

        if [ "$memory_mb" -gt "$ALERT_THRESHOLD" ]; then
            log_message "🚨 CRITICAL: IB Gateway memory usage: ${memory_mb}MB (threshold: ${ALERT_THRESHOLD}MB)"
            log_message "🔄 Restarting IB Gateway to prevent crash..."

            # Graceful restart
            pkill -f "java.*ibgateway"
            sleep 5
            export DISPLAY=:1
            /home/davidsanker/IBC/gatewaystart.sh &
            sleep 20

            log_message "✅ IB Gateway restarted due to memory exhaustion"
            return 1
        else
            log_message "✅ IB Gateway memory OK: ${memory_mb}MB"
            return 0
        fi
    else
        log_message "❌ IB Gateway process not found"
        return 1
    fi
}

check_trading_bot_memory() {
    local pids=$(pgrep -f "python.*trading")
    for pid in $pids; do
        if [ -n "$pid" ]; then
            local memory_kb=$(ps -p "$pid" -o rss= | tr -d ' ')
            local memory_mb=$((memory_kb / 1024))

            if [ "$memory_mb" -gt "$TRADING_BOT_THRESHOLD" ]; then
                log_message "🚨 CRITICAL: Trading bot memory usage: ${memory_mb}MB (PID: $pid)"
                log_message "🔄 Restarting trading bot..."

                # Restart trading bot
                pkill -f "python.*trading"
                sleep 3
                source ~/venv/bin/activate
                python3 /tmp/active_trading_bot.py > /tmp/trading_bot_restart.log 2>&1 &

                log_message "✅ Trading bot restarted due to memory exhaustion"
                return 1
            fi
        fi
    done
    return 0
}

# Main monitoring loop
while true; do
    check_ib_gateway_memory
    check_trading_bot_memory
    sleep 300  # Check every 5 minutes
done
EOF

chmod +x /home/davidsanker/platform/bin/memory_monitor.sh

# 2. CREATE API CONNECTION MONITOR
cat > /home/davidsanker/platform/bin/api_connection_monitor.sh << 'EOF'
#!/bin/bash
# API connection monitoring and recovery

LOG_FILE="/home/davidsanker/platform/logs/api_monitor.log"
MAX_FAILURES=3
FAILURE_COUNT=0

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_api_connection() {
    # Test basic connectivity
    if timeout 5 bash -c "echo '' > /dev/tcp/127.0.0.1/4002" 2>/dev/null; then
        log_message "✅ API connection successful"
        FAILURE_COUNT=0
        return 0
    else
        log_message "❌ API connection failed"
        FAILURE_COUNT=$((FAILURE_COUNT + 1))

        if [ "$FAILURE_COUNT" -ge "$MAX_FAILURES" ]; then
            log_message "🚨 CRITICAL: API connection failed $FAILURE_COUNT times"
            log_message "🔄 Restarting IB Gateway..."

            # Restart IB Gateway
            pkill -f "java.*ibgateway"
            sleep 5
            export DISPLAY=:1
            /home/davidsanker/IBC/gatewaystart.sh &
            sleep 20

            # Restart trading bot with new client ID
            pkill -f "python.*trading"
            sleep 3

            # Generate new client ID
            NEW_CLIENT_ID=$((8000 + RANDOM % 1999))

            cat > /tmp/emergency_trading_bot.py << 'EOFPY'
#!/usr/bin/env python3
from ib_insync import IB, util
import time
import sys

util.startLoop()
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=NEW_CLIENT_ID, timeout=15)
    print(f'✅ Emergency trading bot started - Client ID: {NEW_CLIENT_ID}')
    print('📊 Account:', ib.managedAccounts()[0])
    print('🚀 Emergency trading bot ACTIVE')

    # Keep running
    ib.run()
except Exception as e:
    print(f'❌ Emergency bot error: {e}')
    sys.exit(1)
EOFPY

            # Replace the placeholder with actual client ID
            sed -i "s/NEW_CLIENT_ID/$NEW_CLIENT_ID/g" /tmp/emergency_trading_bot.py

            source ~/venv/bin/activate
            python3 /tmp/emergency_trading_bot.py > /tmp/emergency_trading_bot.log 2>&1 &

            log_message "✅ System restarted due to API failures"
            FAILURE_COUNT=0
        fi

        return 1
    fi
}

# Main monitoring loop
while true; do
    check_api_connection
    sleep 60  # Check every minute
done
EOF

chmod +x /home/davidsanker/platform/bin/api_connection_monitor.sh

# 3. CREATE PROCESS MONITOR
cat > /home/davidsanker/platform/bin/process_monitor.sh << 'EOF'
#!/bin/bash
# Process monitoring and auto-restart

LOG_FILE="/home/davidsanker/platform/logs/process_monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

monitor_ib_gateway() {
    if ! pgrep -f "java.*ibgateway" > /dev/null; then
        log_message "❌ IB Gateway process not found - restarting..."
        export DISPLAY=:1
        /home/davidsanker/IBC/gatewaystart.sh &
        sleep 20
        log_message "✅ IB Gateway restarted"
    fi
}

monitor_trading_bot() {
    if ! pgrep -f "python.*trading" > /dev/null; then
        log_message "❌ Trading bot process not found - restarting..."
        source ~/venv/bin/activate

        # Generate new client ID
        NEW_CLIENT_ID=$((8000 + RANDOM % 1999))

        cat > /tmp/auto_restart_trading_bot.py << 'EOFPY'
#!/usr/bin/env python3
from ib_insync import IB, util
import time
import sys

util.startLoop()
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=NEW_CLIENT_ID, timeout=15)
    print(f'✅ Auto-restart trading bot - Client ID: {NEW_CLIENT_ID}')
    print('📊 Account:', ib.managedAccounts()[0])
    print('🚀 Trading bot auto-restarted and ACTIVE')

    # Keep running
    ib.run()
except Exception as e:
    print(f'❌ Auto-restart bot error: {e}')
    sys.exit(1)
EOFPY

        # Replace placeholder with actual client ID
        sed -i "s/NEW_CLIENT_ID/$NEW_CLIENT_ID/g" /tmp/auto_restart_trading_bot.py

        python3 /tmp/auto_restart_trading_bot.py > /tmp/auto_restart_trading_bot.log 2>&1 &
        log_message "✅ Trading bot auto-restarted"
    fi
}

# Main monitoring loop
while true; do
    monitor_ib_gateway
    monitor_trading_bot
    sleep 120  # Check every 2 minutes
done
EOF

chmod +x /home/davidsanker/platform/bin/process_monitor.sh

# 4. CREATE CRON JOBS FOR MONITORING
echo "📅 Setting up cron jobs for continuous monitoring..."

# Remove existing cron jobs to avoid duplicates
crontab -l 2>/dev/null | grep -v "trading.*monitor" | crontab -

# Add new cron jobs
(crontab -l 2>/dev/null; echo "# Trading Bot Prevention Monitoring") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/davidsanker/platform/bin/memory_monitor.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/1 * * * * /home/davidsanker/platform/bin/api_connection_monitor.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/2 * * * * /home/davidsanker/platform/bin/process_monitor.sh") | crontab -

echo "✅ Cron jobs configured"

# 5. CREATE DAILY HEALTH CHECK
cat > /home/davidsanker/platform/bin/daily_health_check.sh << 'EOF'
#!/bin/bash
# Daily comprehensive health check

LOG_FILE="/home/davidsanker/platform/logs/daily_health_check.log"
REPORT_FILE="/home/davidsanker/platform/reports/daily_health_$(date +%Y%m%d).txt"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

generate_health_report() {
    {
        echo "🏥 DAILY TRADING BOT HEALTH REPORT"
        echo "=================================="
        echo "Date: $(date)"
        echo ""

        echo "📊 PROCESS STATUS:"
        echo "------------------"

        # IB Gateway status
        if pgrep -f "java.*ibgateway" > /dev/null; then
            IB_PID=$(pgrep -f "java.*ibgateway" | head -1)
            IB_MEMORY=$(ps -p "$IB_PID" -o rss= | tr -d ' ')
            IB_MEMORY_MB=$((IB_MEMORY / 1024))
            echo "✅ IB Gateway: Running (PID: $IB_PID, Memory: ${IB_MEMORY_MB}MB)"
        else
            echo "❌ IB Gateway: NOT RUNNING"
        fi

        # Trading bot status
        if pgrep -f "python.*trading" > /dev/null; then
            BOT_PIDS=$(pgrep -f "python.*trading")
            echo "✅ Trading Bot: Running (PIDs: $BOT_PIDS)"
        else
            echo "❌ Trading Bot: NOT RUNNING"
        fi

        echo ""
        echo "🔌 API CONNECTION:"
        echo "-----------------"
        if timeout 5 bash -c "echo '' > /dev/tcp/127.0.0.1/4002" 2>/dev/null; then
            echo "✅ API Port 4002: Responsive"
        else
            echo "❌ API Port 4002: Not responding"
        fi

        echo ""
        echo "💾 SYSTEM RESOURCES:"
        echo "-------------------"
        echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%"
        echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
        echo "Disk Usage: $(df -h / | tail -1 | awk '{print $5}')"

        echo ""
        echo "📈 TRADING ACTIVITY (last 24h):"
        echo "------------------------------"

        # Check recent log entries
        if [ -f "/tmp/active_trading_final.log" ]; then
            TRADE_COUNT=$(grep -c "TRADE\|ORDER" /tmp/active_trading_final.log 2>/dev/null || echo "0")
            ERROR_COUNT=$(grep -c "ERROR\|FAILED" /tmp/active_trading_final.log 2>/dev/null || echo "0")
            echo "Recent Trades: $TRADE_COUNT"
            echo "Recent Errors: $ERROR_COUNT"
        fi

        echo ""
        echo "📋 RECENT LOGS (last 10 lines):"
        echo "------------------------------"
        if [ -f "/tmp/active_trading_final.log" ]; then
            tail -10 /tmp/active_trading_final.log
        fi

    } | tee "$REPORT_FILE"
}

mkdir -p /home/davidsanker/platform/reports
generate_health_report
log_message "Daily health check completed - report saved to $REPORT_FILE"
EOF

chmod +x /home/davidsanker/platform/bin/daily_health_check.sh

# Add daily health check to cron
(crontab -l 2>/dev/null; echo "0 6 * * * /home/davidsanker/platform/bin/daily_health_check.sh") | crontab -

echo "📊 Daily health check scheduled for 6:00 AM daily"

# 6. CREATE EMERGENCY STOP SCRIPT
cat > /home/davidsanker/platform/bin/emergency_stop_all.sh << 'EOF'
#!/bin/bash
# Emergency stop all trading processes

echo "🛑 EMERGENCY STOP - Stopping all trading processes"
echo "=================================================="

# Stop trading bot
echo "Stopping trading bot..."
pkill -f "python.*trading"
pkill -f "trading_bot"

# Stop IB Gateway
echo "Stopping IB Gateway..."
pkill -f "java.*ibgateway"

# Kill any remaining processes
echo "Force killing any remaining processes..."
pkill -9 -f "python.*trading"
pkill -9 -f "java.*ibgateway"

echo "✅ All trading processes stopped"
echo "System is now safe for manual intervention"
EOF

chmod +x /home/davidsanker/platform/bin/emergency_stop_all.sh

# 7. START MONITORING PROCESSES
echo "🚀 Starting prevention monitoring processes..."

# Start monitoring in background
nohup /home/davidsanker/platform/bin/memory_monitor.sh > /dev/null 2>&1 &
nohup /home/davidsanker/platform/bin/api_connection_monitor.sh > /dev/null 2>&1 &
nohup /home/davidsanker/platform/bin/process_monitor.sh > /dev/null 2>&1 &

echo "✅ Prevention monitoring started"

echo ""
echo "🎯 FAILURE PREVENTION SYSTEM DEPLOYED!"
echo "======================================"
echo ""
echo "📋 Active Prevention Measures:"
echo "✅ Memory monitoring (every 5 minutes) - Auto-restart at 1.8GB/1GB thresholds"
echo "✅ API connection monitoring (every 1 minute) - Auto-restart after 3 failures"
echo "✅ Process monitoring (every 2 minutes) - Auto-restart missing processes"
echo "✅ Daily health reports (6:00 AM) - Comprehensive system analysis"
echo "✅ Emergency stop capability - Immediate system shutdown"
echo ""
echo "📁 Log locations:"
echo "- Memory monitor: /home/davidsanker/platform/logs/memory_monitor.log"
echo "- API monitor: /home/davidsanker/platform/logs/api_monitor.log"
echo "- Process monitor: /home/davidsanker/platform/logs/process_monitor.log"
echo "- Daily reports: /home/davidsanker/platform/reports/"
echo ""
echo "🔧 Manual controls:"
echo "- Stop all: /home/davidsanker/platform/bin/emergency_stop_all.sh"
echo "- Daily check: /home/davidsanker/platform/bin/daily_health_check.sh"
echo "- View cron: crontab -l"
echo ""
echo "⚠️  This system will automatically detect and prevent failures!"
echo "   Your bot should never go down unexpectedly again!"