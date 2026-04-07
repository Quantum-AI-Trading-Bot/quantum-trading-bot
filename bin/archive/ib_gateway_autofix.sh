#!/bin/bash
set -euo pipefail

# ============================================================================
# COMMUNITY WORKAROUND: IB Gateway Auto-Fix Script
# Combines IBC optimization + GUI automation + monitoring
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/autofix_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Install GUI automation tools if not present
install_gui_tools() {
    log "Checking GUI automation tools..."
    if ! command -v xdotool &> /dev/null; then
        log "Installing xdotool and xautomation..."
        sudo apt update && sudo apt install -y xdotool xautomation || {
            log "WARNING: Failed to install GUI tools - continuing without them"
        }
    fi
}

# Update IBC config for community best practices
update_ibc_config() {
    log "Updating IBC configuration for better automation..."

    # Backup original config
    cp /home/davidsanker/IBC/config.ini /home/davidsanker/IBC/config.ini.backup_${TIMESTAMP}

    # Create optimized config
    cat > /home/davidsanker/IBC/config.ini << 'EOF'
# Optimized IBC Configuration for Automation

# Trading Mode
TradingMode=paper
FIX=no

# Authentication
IbLoginId=amakua444
IbPassword=YOUR_IB_PASSWORD
SecondFactorDevice=IBKR Mobile
ReloginAfterSecondFactorAuthenticationTimeout=yes
ExitAfterSecondFactorAuthenticationTimeout=no
SecondFactorAuthenticationTimeout=180
SecondFactorAuthenticationExitInterval=120

# Auto-Restart Settings
AutoLogoffTime=Friday 22:00
AutoRestartTime=07:05
ColdRestartTime=Sunday 07:05

# API Configuration
AcceptIncomingConnectionAction=accept
ReadOnlyApi=no
EnableApi=yes
ApiPort=4002
ApiReadOnly=no

# Memory and Performance
IbAutoClosedown=no

# GUI Automation
MinimizeMainWindow=yes
AcceptNonBrokerageAccountWarning=yes
AllowBlindTrading=yes
ExistingSessionDetectedAction=primary

# Command Server for remote control
CommandServerPort=7462
SuppressInfoMessages=yes

# Diagnostic Settings
LogStructureWhen=never
LogStructureScope=known
EOF

    log "IBC configuration updated successfully"
}

# Enhanced Java memory settings
update_memory_settings() {
    log "Updating Java memory settings for IB Gateway..."

    # Find and update Java VM options
    IBC_START_SCRIPT="/home/davidsanker/IBC/gatewaystart.sh"
    if [ -f "$IBC_START_SCRIPT" ]; then
        # Create backup
        cp "$IBC_START_SCRIPT" "${IBC_START_SCRIPT}.backup_${TIMESTAMP}"

        # Update memory settings (if script contains java options)
        if grep -q "JAVA_VM_OPTIONS" "$IBC_START_SCRIPT"; then
            sed -i 's/-Xmx[0-9]*m/-Xmx2048m/g' "$IBC_START_SCRIPT"
            sed -i 's/-Xmx[0-9]*M/-Xmx2048M/g' "$IBC_START_SCRIPT"
            log "Updated Java memory to 2GB heap"
        fi
    fi
}

# GUI automation functions
auto_login_gui() {
    if command -v xdotool &> /dev/null; then
        log "Attempting GUI automation for login..."

        # Wait for IB Gateway window
        sleep 30

        # Find and activate IB Gateway window
        if xdotool search --name "IB Gateway" windowactivate; then
            log "IB Gateway window found, attempting auto-fill..."

            # Auto-fill credentials
            xdotool type --delay 100 "amakua444"
            xdotool key Tab
            xdotool type --delay 100 "YOUR_IB_PASSWORD"
            xdotool key Return

            log "Credentials auto-filled. Please complete 2FA on mobile device."
            return 0
        else
            log "IB Gateway window not found for automation"
            return 1
        fi
    else
        log "GUI automation tools not available"
        return 1
    fi
}

# Enhanced health check
enhanced_health_check() {
    log "Running enhanced IB Gateway health check..."

    # Check process running
    if ! pgrep -f "java.*ibgateway" > /dev/null; then
        log "❌ IB Gateway process not running"
        return 1
    fi

    # Check port listening
    if ! nc -z 127.0.0.1 4002 2>/dev/null; then
        log "❌ Port 4002 not listening"
        return 1
    fi

    # Check API connectivity (the important test)
    source ~/venv/bin/activate
    if timeout 15 python3 -c "
from ib_insync import IB
import sys
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=10)
    ib.reqCurrentTime()  # This tests if actually authenticated
    print('API_OK')
    ib.disconnect()
except Exception as e:
    print(f'API_FAILED: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "API_OK"; then
        log "✅ IB Gateway API fully functional"
        return 0
    else
        log "❌ IB Gateway not accepting API connections (needs authentication)"
        return 1
    fi
}

# Smart restart with GUI automation
smart_restart() {
    log "Starting smart IB Gateway restart..."

    # Stop current Gateway
    if pgrep -f "java.*ibgateway" > /dev/null; then
        log "Stopping current IB Gateway..."
        pkill -f "java.*ibgateway" || true
        sleep 10
    fi

    # Start Gateway via IBC
    log "Starting IB Gateway via IBC..."
    cd /home/davidsanker/IBC
    DISPLAY=:1 nohup ./gatewaystart.sh -inline > "${LOG_DIR}/smart_restart_${TIMESTAMP}.log" 2>&1 &

    # Wait for startup
    log "Waiting for IB Gateway to initialize (60 seconds)..."
    sleep 60

    # Attempt GUI automation
    if auto_login_gui; then
        log "GUI automation completed - please approve 2FA on mobile"
    fi

    # Final health check
    sleep 30
    if enhanced_health_check; then
        log "✅ Smart restart successful - IB Gateway is fully operational"
        return 0
    else
        log "⚠️ Smart restart completed but authentication may be required"
        return 1
    fi
}

# Main execution
main() {
    log "=========================================="
    log "IB GATEWAY AUTO-FIX (COMMUNITY SOLUTIONS)"
    log "=========================================="

    # Install tools
    install_gui_tools

    # Update configurations
    update_ibc_config
    update_memory_settings

    # Smart restart
    if smart_restart; then
        log "🎉 SUCCESS: IB Gateway is now operational"

        # Create monitoring script
        cat > /home/davidsanker/platform/bin/monitor_gateway.sh << 'EOF'
#!/bin/bash
# Monitor IB Gateway and alert if issues detected
if ! /home/davidsanker/platform/bin/ib_gateway_autofix.sh --health-check; then
    echo "⚠️ IB Gateway needs attention - check authentication"
    # Send email/alert here if desired
fi
EOF
        chmod +x /home/davidsanker/platform/bin/monitor_gateway.sh

        log "💡 Next steps:"
        log "1. Set up monitoring: */5 * * * * /home/davidsanker/platform/bin/monitor_gateway.sh"
        log "2. Configure alerts for authentication requirements"
        log "3. Consider daily restart: 0 7 * * * /home/davidsanker/platform/bin/ib_gateway_autofix.sh"

    else
        log "❌ Issues detected - please check logs and complete manual authentication"
    fi

    log "=========================================="
    log "Auto-fix complete. Log: ${LOG_FILE}"
    log "=========================================="
}

# Health check mode
if [[ "${1:-}" == "--health-check" ]]; then
    enhanced_health_check
else
    main
fi