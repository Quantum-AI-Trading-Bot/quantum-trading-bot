#!/bin/bash
set -euo pipefail

# ============================================================================
# COMPLETE COMMUNITY SOLUTION FOR IB GATEWAY
# Addresses the daily authentication requirement with smart automation
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/complete_solution_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log "=========================================="
log "COMPLETE COMMUNITY SOLUTION FOR IB GATEWAY"
log "=========================================="

# 1. Check current IB Gateway status
log "Step 1: Checking current IB Gateway status..."

if pgrep -f "java.*ibgateway" > /dev/null; then
    log "✅ IB Gateway process is running"

    # Check if API is accessible
    if timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    print('API_READY')
    ib.disconnect()
except:
    print('API_NEEDS_AUTH')
" 2>/dev/null | grep -q "API_READY"; then
        log "✅ IB Gateway is authenticated and API is ready!"
        log "🎉 SUCCESS: Your Quantum AI Trading Bot can connect now"

        # Provide next steps
        log ""
        log "📋 Next Steps:"
        log "1. Start your trading bot: sudo systemctl start trading-bot.service"
        log "2. Monitor with: /home/davidsanker/platform/bin/status_dashboard.sh"
        log "3. Set up daily automation with: ./daily_auth_window.sh"

        log ""
        log "💡 Monitoring Setup:"
        log "Add to crontab for automated monitoring:"
        echo "*/5 * * * * /home/davidsanker/platform/bin/ib_gateway_monitor.sh"

        exit 0
    else
        log "⚠️ IB Gateway is running but needs authentication"
    fi
else
    log "❌ IB Gateway is not running - starting it..."
fi

# 2. Start IB Gateway if not running
if ! pgrep -f "java.*ibgateway" > /dev/null; then
    log "Starting IB Gateway..."
    export DISPLAY=:1
    cd /home/davidsanker
    nohup /home/davidsanker/IBGateway/ibgateway.bin > "${LOG_DIR}/gateway_startup_${TIMESTAMP}.log" 2>&1 &

    # Wait for GUI to initialize
    log "Waiting for IB Gateway GUI to initialize..."
    sleep 30

    if pgrep -f "java.*ibgateway" > /dev/null; then
        log "✅ IB Gateway started successfully"
    else
        log "❌ Failed to start IB Gateway"
        exit 1
    fi
fi

# 3. GUI Automation Setup
log "Step 3: Setting up GUI automation..."

# Create enhanced GUI automation script
cat > /home/davidsanker/platform/bin/auto_login_gui.sh << 'EOF'
#!/bin/bash
set -e

export DISPLAY=:1

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Find and activate IB Gateway window
WINDOW_ID=$(xdotool search --class "Gateway" | head -1)
if [ -z "$WINDOW_ID" ]; then
    log "❌ IB Gateway window not found"
    exit 1
fi

log "Found IB Gateway window: $WINDOW_ID"

# Bring window to front (multiple methods)
xdotool windowactivate "$WINDOW_ID" || true
xdotool windowraise "$WINDOW_ID" || true
sleep 2

# Clear any existing text and enter credentials
log "Entering credentials..."
xdotool key "Ctrl+a"  # Select all
sleep 0.5
xdotool type "amakua444"  # Username
sleep 0.5
xdotool key Tab
sleep 0.5
xdotool type "YOUR_IB_PASSWORD"  # Password
sleep 0.5
xdotool key Return

log "✅ Credentials entered - please complete 2FA on your mobile device"
EOF

chmod +x /home/davidsanker/platform/bin/auto_login_gui.sh

# 4. Create Monitoring Script
cat > /home/davidsanker/platform/bin/ib_gateway_monitor.sh << 'EOF'
#!/bin/bash

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/monitor_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

# Check IB Gateway status
check_gateway_status() {
    if pgrep -f "java.*ibgateway" > /dev/null; then
        # Check API connectivity
        if timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    print('OK')
    ib.disconnect()
except:
    print('AUTH_NEEDED')
" 2>/dev/null | grep -q "OK"; then
            echo "HEALTHY"
        else
            echo "NEEDS_AUTH"
        fi
    else
        echo "DOWN"
    fi
}

# Get current status
STATUS=$(check_gateway_status)

case "$STATUS" in
    "HEALTHY")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ IB Gateway is healthy and authenticated" >> "${LOG_FILE}"
        ;;
    "NEEDS_AUTH")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ IB Gateway needs authentication" >> "${LOG_FILE}"
        # Create alert
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🚨 ALERT: IB Gateway requires manual authentication" >> "${LOG_DIR}/alerts.log"
        echo "Please access VNC (localhost:5901) and complete login" >> "${LOG_DIR}/alerts.log"
        ;;
    "DOWN")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ IB Gateway is down - attempting restart" >> "${LOG_FILE}"
        # Try to restart
        /home/davidsanker/platform/bin/complete_community_solution.sh
        ;;
esac
EOF

chmod +x /home/davidsanker/platform/bin/ib_gateway_monitor.sh

# 5. Create Daily Authentication Window Script
cat > /home/davidsanker/platform/bin/daily_auth_window.sh << 'EOF'
#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "🌅 Daily IB Gateway Authentication Window"

# Ensure IB Gateway is running
if ! pgrep -f "java.*ibgateway" > /dev/null; then
    log "Starting IB Gateway..."
    export DISPLAY=:1
    cd /home/davidsanker
    nohup /home/davidsanker/IBGateway/ibgateway.bin > /tmp/daily_gateway.log 2>&1 &
    sleep 45
fi

# Run GUI automation
log "Running GUI automation for login..."
/home/davidsanker/platform/bin/auto_login_gui.sh

log "✅ Daily authentication setup complete"
log "💡 Reminder: Complete 2FA on your mobile device within 3 minutes"
EOF

chmod +x /home/davidsanker/platform/bin/daily_auth_window.sh

# 6. Current Status and Next Steps
log "Step 4: Current Status and Instructions"

log ""
log "📊 CURRENT STATUS:"
if pgrep -f "java.*ibgateway" > /dev/null; then
    log "✅ IB Gateway Process: Running (PID: $(pgrep -f "java.*ibgateway"))"
    log "⚠️ API Status: Needs Authentication"
    log "🖥️ GUI Status: Available at DISPLAY=:1"
else
    log "❌ IB Gateway: Not Running"
fi

log ""
log "🎯 IMMEDIATE ACTION REQUIRED:"
log "1. Connect via VNC: vnc://localhost:5901"
log "2. Complete the login with your credentials"
log "3. Approve the 2FA notification on your IBKR Mobile app"
log "4. Wait for 'Active trading enabled' message"

log ""
log "🤖 AUTOMATION OPTIONS:"

if pgrep -f "java.*ibgateway" > /dev/null; then
    log "Option A - Quick GUI Automation:"
    log "   /home/davidsanker/platform/bin/auto_login_gui.sh"
    log "   (Then complete 2FA on mobile)"

    log ""
    log "Option B - VNC Manual Login:"
    log "   Connect to: vnc://localhost:5901"
    log "   Enter credentials manually"
fi

log ""
log "📅 SCHEDULED AUTOMATION SETUP:"
echo "0 7 * * * /home/davidsanker/platform/bin/daily_auth_window.sh  # Daily 7 AM auth"
echo "*/5 * * * * /home/davidsanker/platform/bin/ib_gateway_monitor.sh   # Monitor every 5 min"

log ""
log "🔧 TROUBLESHOOTING:"
log "- If GUI automation fails: Use VNC to connect manually"
log "- If port 4002 blocked: Check firewall settings"
log "- If memory issues: Monitor Java process with 'top'"
log "- If login fails: Verify credentials in config.ini"

log ""
log "📈 SUCCESS METRICS:"
log "- ✅ IB Gateway should run continuously"
log "- ✅ Daily authentication keeps API alive"
log "- ✅ Trading bot can connect after auth"
log "- ✅ Monitoring alerts on issues"

log ""
log "=========================================="
log "COMMUNITY SOLUTION SETUP COMPLETE!"
log "=========================================="
log "Log file: ${LOG_FILE}"

# Provide immediate next command
log ""
log "🚀 NEXT COMMAND TO RUN:"
if pgrep -f "java.*ibgateway" > /dev/null; then
    log "/home/davidsanker/platform/bin/auto_login_gui.sh"
else
    log "echo 'Please wait for IB Gateway to start, then run the auto-login script'"
fi

log ""
log "📋 CHECKLIST:"
log "☐ Complete manual authentication via VNC or GUI automation"
log "☐ Verify API connectivity with: python3 -c 'from ib_insync import IB; ib=IB(); ib.connect(\"127.0.0.1\",4002,clientId=999)'"
log "☐ Start trading bot: sudo systemctl start trading-bot.service"
log "☐ Set up cron jobs for daily automation"
log "☐ Test the monitoring system"