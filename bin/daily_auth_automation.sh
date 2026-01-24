#!/bin/bash
#
# Daily Authentication Automation for IB Gateway
# Handles the 24-hour mandatory authentication reset
#
# Schedule: Run via cron every 12 hours
# Purpose: Ensure permanent connection with automatic 2FA handling
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/home/davidsanker/platform/logs/ib-gateway/daily-auth.log"
VNC_DISPLAY=":1"
IB_ACCOUNT="amakua444"
NOTIFICATION_EMAIL="david@sanker.at"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Send notification
send_notification() {
    local subject="$1"
    local message="$2"

    if command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL"
        log "📧 Notification sent: $subject"
    fi
}

# Check IB Gateway status
check_ib_status() {
    # Check if process is running
    if ! pgrep -f "ibcalpha.ibc.IbcGateway" >/dev/null; then
        log "❌ IB Gateway process is not running"
        return 1
    fi

    # Check if API port is responsive
    if ! timeout 5 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
        log "⚠️  IB Gateway is running but API port 4002 is not responsive"
        return 2
    fi

    log "✅ IB Gateway is healthy and responsive"
    return 0
}

# Perform authentication check
check_authentication() {
    log "🔐 Checking authentication status..."

    export DISPLAY="$VNC_DISPLAY"
    export XAUTHORITY="$HOME/.Xauthority"

    # Try to connect via Python to test authentication
    python3 -c "
import sys
from ib_insync import IB, util

try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=9999, timeout=10)

    # Try to get account data (requires valid authentication)
    accounts = ib.managedAccounts()
    if accounts:
        print('AUTH_OK')
    else:
        print('AUTH_FAIL')

    ib.disconnect()

except Exception as e:
    print(f'AUTH_ERROR: {e}')
    sys.exit(1)
" 2>>"$LOG_FILE"
}

# Handle authentication window
handle_authentication() {
    log "🔑 Handling authentication window..."

    export DISPLAY="$VNC_DISPLAY"
    export XAUTHORITY="$HOME/.Xauthority"

    # Wait for login window to appear
    local timeout=60
    while [ $timeout -gt 0 ]; do
        if xwininfo -name "IB Gateway" >/dev/null 2>&1 || xwininfo -name "Login" >/dev/null 2>&1; then
            log "🪟 Authentication window detected"
            break
        fi
        sleep 1
        ((timeout--))
    done

    if [ $timeout -eq 0 ]; then
        log "⚠️  No authentication window found within timeout"
        return 1
    fi

    # Focus the window
    local window_name
    if xwininfo -name "IB Gateway" >/dev/null 2>&1; then
        window_name="IB Gateway"
    else
        window_name="Login"
    fi

    local window_id
    window_id=$(xwininfo -name "$window_name" | grep "Window id" | awk '{print $4}')

    if [ -n "$window_id" ]; then
        xdotool windowfocus "$window_id"
        xdotool windowactivate "$window_id"
        log "🎯 Focused authentication window: $window_name"
    fi

    # Wait for manual 2FA (this is unavoidable)
    log "⏰ Waiting for manual 2FA authentication (2 minutes)..."
    log "📱 Please check your IBKR Mobile app for 2FA prompt"

    # Send notification about 2FA
    send_notification "IB Gateway 2FA Required" \
        "IB Gateway requires manual 2FA authentication. Please check your mobile device and complete authentication within 2 minutes."

    sleep 120  # 2 minutes for 2FA

    # Check if authentication completed
    local auth_result
    auth_result=$(check_authentication)

    case "$auth_result" in
        "AUTH_OK")
            log "✅ Authentication completed successfully"
            return 0
            ;;
        *)
            log "❌ Authentication failed or incomplete: $auth_result"
            return 1
            ;;
    esac
}

# Restart IB Gateway if needed
restart_ib_gateway() {
    log "🔄 Restarting IB Gateway..."

    # Stop existing process
    /home/davidsanker/platform/bin/permanent_ib_gateway.sh stop
    sleep 10

    # Start with enhanced script
    /home/davidsanker/platform/bin/permanent_ib_gateway.sh start

    # Wait for startup
    local timeout=300  # 5 minutes
    while [ $timeout -gt 0 ]; do
        if check_ib_status >/dev/null 2>&1; then
            log "✅ IB Gateway restarted and healthy"
            return 0
        fi
        sleep 10
        ((timeout-=10))
    done

    log "❌ IB Gateway failed to restart properly"
    return 1
}

# Main execution
main() {
    local action="${1:-check}"

    case "$action" in
        "check")
            log "🔍 Running daily authentication check..."

            # Check current status
            if check_ib_status >/dev/null 2>&1; then
                log "✅ IB Gateway is healthy, checking authentication..."

                # Test authentication
                local auth_result
                auth_result=$(check_authentication)

                case "$auth_result" in
                    "AUTH_OK")
                        log "🎉 IB Gateway is fully authenticated and operational"
                        exit 0
                        ;;
                    *)
                        log "⚠️  Authentication issue detected: $auth_result"
                        log "🔑 Attempting to handle authentication..."

                        if handle_authentication; then
                            log "✅ Authentication handled successfully"
                            send_notification "IB Gateway Authentication Success" \
                                "IB Gateway authentication completed successfully. Trading operations resumed."
                        else
                            log "❌ Authentication handling failed, restarting..."
                            restart_ib_gateway
                            send_notification "IB Gateway Restarted" \
                                "IB Gateway was restarted due to authentication issues. Please verify trading operations."
                        fi
                        ;;
                esac
            else
                log "❌ IB Gateway is not healthy, attempting restart..."
                restart_ib_gateway
                send_notification "IB Gateway Emergency Restart" \
                    "IB Gateway was automatically restarted due to connection issues. Please verify system status."
            fi
            ;;

        "force-restart")
            log "🔄 Force restarting IB Gateway..."
            restart_ib_gateway
            ;;

        "status")
            if check_ib_status >/dev/null 2>&1; then
                log "✅ IB Gateway is healthy"

                local auth_result
                auth_result=$(check_authentication)

                case "$auth_result" in
                    "AUTH_OK")
                        log "✅ Authentication is valid"
                        ;;
                    *)
                        log "⚠️  Authentication issue: $auth_result"
                        ;;
                esac
            else
                log "❌ IB Gateway needs attention"
            fi
            ;;

        *)
            echo "Usage: $0 {check|force-restart|status}"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"