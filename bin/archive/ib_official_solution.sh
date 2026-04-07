#!/bin/bash
set -euo pipefail

# ============================================================================
# OFFICIAL IBC SOLUTION: Pure IBC Configuration (No GUI Automation)
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/official_solution_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Create official IBC configuration only
create_official_ibc_config() {
    log "Creating official IBC-only configuration..."

    # Backup original
    cp /home/davidsanker/IBC/config.ini /home/davidsanker/IBC/config.ini.official_backup_${TIMESTAMP}

    # Official IBC config (no GUI automation)
    cat > /home/davidsanker/IBC/config.ini << 'EOF'
# ============================================================================
# OFFICIAL IBC CONFIGURATION - No GUI Automation Required
# ============================================================================

# IBC Startup Settings
FIX=no

# Authentication Settings
IbLoginId=amakua444
IbPassword=YOUR_IB_PASSWORD
SecondFactorDevice=IBKR Mobile

# Critical for 24-hour automation
ReloginAfterSecondFactorAuthenticationTimeout=yes
ExitAfterSecondFactorAuthenticationTimeout=no
SecondFactorAuthenticationTimeout=180
SecondFactorAuthenticationExitInterval=120

# Trading Mode
TradingMode=paper
AcceptNonBrokerageAccountWarning=yes

# Login Dialog Management
LoginDialogDisplayTimeout=60

# Window Management
MinimizeMainWindow=yes
ExistingSessionDetectedAction=primary

# API Configuration (Official)
AcceptIncomingConnectionAction=accept
ReadOnlyApi=no
EnableApi=yes
ApiPort=4002
ApiReadOnly=no

# Official IB Auto-Restart Strategy
# This leverages IB's official schedule + Cold Restart for weekends
AutoLogoffTime=
AutoRestartTime=11:00 PM  # Official auto-restart
ColdRestartTime=Sunday 07:05  # Weekly full re-auth

# Command Server for Remote Control (Official)
CommandServerPort=7462
CommandPrompt=IBC>
SuppressInfoMessages=yes
BindAddress=
ControlFrom=

# Memory and Performance (Official)
IbAutoClosedown=no

# Security Settings (Official)
AllowBlindTrading=yes

# Order Management (Official)
ConfirmOrderIdReset=confirm/confirm

# Diagnostic Settings (Minimal for Production)
LogStructureWhen=never
LogStructureScope=known
LogComponents=
EOF

    log "Official IBC configuration created"
}

# Update systemd service for official approach
update_systemd_service() {
    log "Updating systemd service for official IBC approach..."

    # Create enhanced service file
    sudo tee /etc/systemd/system/ib-gateway.service > /dev/null << 'EOF'
[Unit]
Description=Interactive Brokers Gateway - Official IBC Configuration
Documentation=https://github.com/IbcAlpha/IBC
After=network.target xvfb.service
Wants=xvfb.service

[Service]
Type=forking
User=davidsanker
WorkingDirectory=/home/davidsanker
Environment=DISPLAY=:1
Environment=HOME=/home/davidsanker

# Enhanced Pre-start Checks
ExecStartPre=/bin/bash -c 'pgrep -x Xvfb > /dev/null || { echo "ERROR: Xvfb not running"; exit 1; }'
ExecStartPre=/bin/bash -c 'test -f /home/davidsanker/IBC/config.ini || { echo "ERROR: IBC config missing"; exit 1; }'
ExecStartPre=/bin/bash -c 'test -x /home/davidsanker/IBC/gatewaystart.sh || { echo "ERROR: gatewaystart.sh not executable"; exit 1; }'

# Main IBC Startup (Official)
ExecStart=/home/davidsanker/IBC/gatewaystart.sh -inline

# Official Health Checks
ExecStartPost=/bin/bash -c 'sleep 30; for i in {1..12}; do timeout 5 /home/davidsanker/platform/bin/ib_official_solution.sh --check-api && exit 0; sleep 10; done; echo "WARNING: IB Gateway not ready after 2 minutes"'

# Enhanced Shutdown Procedure
ExecStop=/bin/bash -c 'echo "STOP" | nc localhost 7462 || pkill -f "java.*ibgateway"'
ExecStopPost=/bin/sleep 10

# Enhanced Restart Policy (Official)
Restart=on-failure
RestartSec=60
StartLimitBurst=3
StartLimitIntervalSec=600

# Enhanced Resource Limits (Official)
MemoryLimit=4G
MemoryHigh=3G
OOMScoreAdjust=-100
CPUQuota=80%

# Enhanced Logging (Official)
StandardOutput=append:/home/davidsanker/platform/logs/ib-gateway/service.log
StandardError=append:/home/davidsanker/platform/logs/ib-gateway/service-error.log
SyslogIdentifier=ib-gateway

# Security (Official)
PrivateTmp=yes
ProtectSystem=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload
    sudo systemctl enable ib-gateway.service

    log "Systemd service updated with official IBC configuration"
}

# Create authentication monitoring script
create_auth_monitor() {
    log "Creating official authentication monitoring..."

    cat > /home/davidsanker/platform/bin/auth_monitor.sh << 'EOF'
#!/bin/bash
# Official IBC Authentication Monitor

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
LOG_FILE="${LOG_DIR}/auth_monitor_${TIMESTAMP}.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

check_ib_status() {
    # Check if process is running
    if ! pgrep -f "java.*ibgateway" > /dev/null; then
        log "❌ IB Gateway process not running"
        return 1
    fi

    # Check if port is listening
    if ! nc -z 127.0.0.1 4002 2>/dev/null; then
        log "❌ Port 4002 not available"
        return 1
    fi

    # Check API authentication status
    source ~/venv/bin/activate
    if timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    accounts = ib.managedAccounts()
    print(f'AUTH_OK: {accounts[0] if accounts else \"NO_ACCOUNTS\"}')
    ib.disconnect()
except Exception as e:
    print(f'AUTH_FAILED: {e}')
    exit(1)
" 2>/dev/null | grep -q "AUTH_OK"; then
        log "✅ IB Gateway authenticated and ready"
        return 0
    else
        log "⚠️ IB Gateway running but needs authentication"
        return 1
    fi
}

send_alert() {
    local message="$1"
    log "🚨 ALERT: $message"

    # Here you can add email/SMS/Slack notifications
    # For now, create alert file
    echo "[$(date)] $message" >> /home/davidsanker/platform/logs/ib-gateway/alerts.log

    # You could add:
    # sendmail ... (email)
    # curl ... (Slack webhook)
    # wget ... (SMS service)
}

# Main monitoring logic
if ! check_ib_status; then
    send_alert "IB Gateway requires manual authentication. Please access VNC and complete login."

    # Check if this is during trading hours
    current_hour=$(date +%H)
    if [[ $current_hour -ge 9 && $current_hour -le 16 ]]; then
        send_alert "CRITICAL: Authentication needed during trading hours!"
    fi
fi
EOF

    chmod +x /home/davidsanker/platform/bin/auth_monitor.sh
    log "Authentication monitor created"
}

# Set up official monitoring schedule
setup_monitoring() {
    log "Setting up official monitoring schedule..."

    # Create cron entries
    (crontab -l 2>/dev/null; echo "# IB Gateway Official Monitoring") | crontab -
    (crontab -l 2>/dev/null; echo "*/5 * * * * /home/davidsanker/platform/bin/auth_monitor.sh") | crontab -
    (crontab -l 2>/dev/null; echo "# Daily status report") | crontab -
    (crontab -l 2>/dev/null; echo "0 8 * * * /home/davidsanker/platform/bin/ib_official_solution.sh --status") | crontab -

    log "Monitoring schedule configured"
}

# API check function
check_api() {
    source ~/venv/bin/activate
    timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    ib.reqCurrentTime()
    print('OK')
    ib.disconnect()
except:
    exit(1)
"
}

# Status report
status_report() {
    log "=========================================="
    log "IB GATEWAY OFFICIAL STATUS REPORT"
    log "=========================================="

    # Process status
    if pgrep -f "java.*ibgateway" > /dev/null; then
        log "✅ Process: Running (PID: $(pgrep -f "java.*ibgateway"))"
    else
        log "❌ Process: Not running"
    fi

    # Port status
    if nc -z 127.0.0.1 4002 2>/dev/null; then
        log "✅ Port 4002: Listening"
    else
        log "❌ Port 4002: Not available"
    fi

    # API status
    if check_api >/dev/null 2>&1; then
        log "✅ API: Authenticated and functional"
    else
        log "❌ API: Not ready (needs authentication)"
    fi

    # Recent alerts
    if [ -f "/home/davidsanker/platform/logs/ib-gateway/alerts.log" ]; then
        log "📋 Recent Alerts:"
        tail -5 /home/davidsanker/platform/logs/ib-gateway/alerts.log | sed 's/^/   /'
    fi

    log "=========================================="
}

# Main implementation
main() {
    log "=========================================="
    log "OFFICIAL IBC SOLUTION IMPLEMENTATION"
    log "=========================================="

    # Implement official configuration
    create_official_ibc_config
    update_systemd_service
    create_auth_monitor
    setup_monitoring

    log "✅ Official IBC solution implemented"
    log ""
    log "📋 Next Steps:"
    log "1. Start the service: sudo systemctl start ib-gateway"
    log "2. Monitor logs: journalctl -u ib-gateway -f"
    log "3. Complete manual authentication: VNC to localhost:5901"
    log "4. Verify status: /home/davidsanker/platform/bin/ib_official_solution.sh --status"
    log ""
    log "📅 Important:"
    log "- Daily authentication required (IB security policy)"
    log "- Weekly full re-auth on Sunday 07:05 (Cold Restart)"
    log "- Monitor will alert when authentication needed"
    log "- Check status daily with --status flag"
}

# Handle command line arguments
case "${1:-}" in
    --check-api)
        check_api
        ;;
    --status)
        status_report
        ;;
    *)
        main
        ;;
esac