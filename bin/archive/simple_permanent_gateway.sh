#!/bin/bash
#
# Simplified Permanent IB Gateway Solution
# Works with your existing manual VNC login approach
#
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/home/davidsanker/platform/logs/ib-gateway/simple-permanent.log"
PID_FILE="/tmp/ib_gateway_simple.pid"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if VNC is working
check_vnc() {
    export DISPLAY=:1
    if ! xdpyinfo >/dev/null 2>&1; then
        log "❌ VNC display :1 is not available"
        return 1
    fi
    log "✅ VNC display is working"
    return 0
}

# Start IB Gateway with your current working method
start_ib_gateway() {
    log "🚀 Starting IB Gateway with proven method..."

    export DISPLAY=:1
    export XAUTHORITY="$HOME/.Xauthority"

    # Kill existing processes
    pkill -f "ibgateway" || true
    sleep 3

    # Start with your working method
    /home/davidsanker/IBGateway/ibgateway.bin &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    log "✅ IB Gateway started with PID: $pid"
    log "📱 Please complete 2FA authentication in VNC if required"

    return 0
}

# Health check
health_check() {
    log "🏥 Performing health checks..."

    # Check if process is running
    if ! pgrep -f "ibgateway" >/dev/null; then
        log "❌ IB Gateway process is not running"
        return 1
    fi

    # Check API port
    local timeout=180  # 3 minutes for authentication
    local check_interval=10

    while [ $timeout -gt 0 ]; do
        if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
            log "✅ API port 4002 is responsive"
            return 0
        fi
        log "⏳ Waiting for API authentication... (${timeout}s remaining)"
        sleep $check_interval
        ((timeout-=check_interval))
    done

    log "❌ Health check failed - API port not responsive within timeout"
    return 1
}

# Start simple monitoring
start_monitoring() {
    log "📊 Starting simple monitoring daemon..."

    cat > "/tmp/simple_ib_monitor.sh" << 'EOF'
#!/bin/bash
# Simple IB Gateway Monitor

MONITOR_INTERVAL=300  # Check every 5 minutes
API_PORT=4002
LOG_FILE="/home/davidsanker/platform/logs/ib-gateway/simple-permanent.log"

while true; do
    if ! pgrep -f "ibgateway" >/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] IB Gateway process died - restarting" >> "$LOG_FILE"
        /home/davidsanker/platform/bin/simple_permanent_gateway.sh start &
    fi

    sleep $MONITOR_INTERVAL
done
EOF

    chmod +x "/tmp/simple_ib_monitor.sh"

    # Start monitor in background
    /tmp/simple_ib_monitor.sh &
    local monitor_pid=$!
    echo "$monitor_pid" > "/tmp/simple_ib_monitor.pid"

    log "✅ Simple monitoring daemon started with PID: $monitor_pid"
}

# Main function
main() {
    local action="${1:-start}"

    case "$action" in
        "start")
            log "🚀 Starting Simplified Permanent IB Gateway Solution"

            if ! check_vnc; then
                log "❌ VNC check failed - please start VNC first"
                exit 1
            fi

            start_ib_gateway

            if health_check; then
                log "✅ IB Gateway started successfully and is healthy"
                start_monitoring
                log "🎉 Simplified Permanent IB Gateway is now running"
                log "📊 API Port: 4002"
                log "🖥️  VNC Display: :1"
                log "📝 Logs: $LOG_FILE"
            else
                log "⚠️  IB Gateway started but needs manual authentication"
                log "📱 Please authenticate via VNC at localhost:5901"
                start_monitoring
            fi
            ;;

        "stop")
            log "🛑 Stopping Simplified IB Gateway..."

            # Kill monitor
            if [ -f "/tmp/simple_ib_monitor.pid" ]; then
                kill "$(cat /tmp/simple_ib_monitor.pid)" || true
                rm -f "/tmp/simple_ib_monitor.pid"
            fi

            # Kill main process
            pkill -f "ibgateway" || true
            rm -f "$PID_FILE"

            log "✅ Simplified IB Gateway stopped"
            ;;

        "status")
            if pgrep -f "ibgateway" >/dev/null; then
                log "✅ IB Gateway is running"
                if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
                    log "✅ API port 4002 is responsive"
                else
                    log "⚠️  API port 4002 is not responsive (needs authentication)"
                fi
            else
                log "❌ IB Gateway is not running"
            fi
            ;;

        *)
            echo "Usage: $0 {start|stop|status}"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"