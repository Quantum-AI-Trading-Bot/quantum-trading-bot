#!/bin/bash
#
# Enhanced IB Gateway Startup Script for 24/7 Permanent Operation
# Solves the manual VNC works / automatic fails problem
#
# Created: 2024-12-10
# Purpose: Permanent IB Gateway connection with advanced automation
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TWS_PATH="/home/davidsanker/IBGateway"
IBC_PATH="/home/davidsanker/IBC"
CONFIG_FILE="$IBC_PATH/config.ini"
LOG_FILE="/home/davidsanker/platform/logs/ib-gateway/enhanced-startup.log"
VNC_DISPLAY=":1"
PID_FILE="/tmp/ib_gateway_enhanced.pid"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if VNC is running
check_vnc() {
    if ! (pgrep -f "tightvnc :1" > /dev/null || pgrep -f "Xvnc :1" > /dev/null); then
        log "❌ VNC server is not running on $VNC_DISPLAY"
        log "🚀 Starting VNC server..."

        # Start VNC server
        vncserver :1 -geometry 1920x1080 -depth 24 2>&1 | tee -a "$LOG_FILE"
        sleep 3

        if ! (pgrep -f "tightvnc :1" > /dev/null || pgrep -f "Xvnc :1" > /dev/null); then
            log "❌ Failed to start VNC server"
            exit 1
        fi
        log "✅ VNC server started successfully"
    else
        log "✅ VNC server is already running"
    fi

    # Always verify X11 is working
    if ! xdpyinfo -display "$VNC_DISPLAY" >/dev/null 2>&1; then
        log "❌ X11 display is not responding"
        exit 1
    fi
    log "✅ X11 display is working"
}

# Prepare X11 environment
prepare_x11() {
    log "🖥️  Preparing X11 environment..."

    export DISPLAY="$VNC_DISPLAY"
    export XAUTHORITY="$HOME/.Xauthority"

    # Wait for X server to be ready
    local timeout=30
    while [ $timeout -gt 0 ]; do
        if xdpyinfo -display "$VNC_DISPLAY" >/dev/null 2>&1; then
            log "✅ X11 display is ready"
            break
        fi
        sleep 1
        ((timeout--))
    done

    if [ $timeout -eq 0 ]; then
        log "❌ X11 display failed to initialize"
        exit 1
    fi
}

# Kill existing IB Gateway processes
cleanup_existing() {
    log "🧹 Cleaning up existing IB Gateway processes..."

    # Kill existing Java processes related to IB Gateway
    pkill -f "ibcalpha.ibc.IbcGateway" || true
    pkill -f "IBGateway" || true

    # Wait for processes to die
    sleep 5

    # Force kill if still running
    pkill -9 -f "ibcalpha.ibc.IbcGateway" || true
    pkill -9 -f "IBGateway" || true

    log "✅ Cleanup completed"
}

# Advanced GUI automation setup
setup_gui_automation() {
    log "🤖 Setting up advanced GUI automation..."

    # Install required automation tools if not present
    if ! command -v xdotool >/dev/null 2>&1; then
        log "⚠️  xdotool not found - GUI automation may fail"
    fi

    if ! command -v xwininfo >/dev/null 2>&1; then
        log "⚠️  xwininfo not found - Window detection may fail"
    fi

    # Create authentication helper script
    cat > "/tmp/ib_auth_helper.sh" << 'EOF'
#!/bin/bash
# IB Authentication Helper for GUI automation

export DISPLAY=:1
export XAUTHORITY="$HOME/.Xauthority"

# Wait for IB Gateway window to appear
timeout=120
while [ $timeout -gt 0 ]; do
    if xwininfo -name "IB Gateway" >/dev/null 2>&1; then
        echo "IB Gateway window detected"
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "IB Gateway window not found within timeout"
    exit 1
fi

# Focus the window
WINDOW_ID=$(xwininfo -name "IB Gateway" | grep "Window id" | awk '{print $4}')
xdotool windowfocus "$WINDOW_ID"
xdotool windowactivate "$WINDOW_ID"

sleep 2

# Handle login dialog (if present)
if xwininfo -name "Login" >/dev/null 2>&1; then
    echo "Login dialog detected"
    LOGIN_WINDOW_ID=$(xwininfo -name "Login" | grep "Window id" | awk '{print $4}')
    xdotool windowfocus "$LOGIN_WINDOW_ID"
    xdotool windowactivate "$LOGIN_WINDOW_ID"

    # Wait for user to handle 2FA manually if needed
    echo "Waiting for manual authentication (30s)..."
    sleep 30
fi

echo "Authentication helper completed"
EOF

    chmod +x "/tmp/ib_auth_helper.sh"
    log "✅ GUI automation helper created"
}

# Enhanced IBC startup
start_enhanced_ibc() {
    log "🚀 Starting Enhanced IBC Gateway..."

    # Prepare environment
    export DISPLAY="$VNC_DISPLAY"
    export XAUTHORITY="$HOME/.Xauthority"

    # Enhanced Java options for stability
    cd "$IBC_PATH"

    # IB Gateway classpath
    IBG_JARS="$TWS_PATH/jars/*:$TWS_PATH/1037/jars/*"
    IBG_INSTALL4J="$TWS_PATH/.install4j/*.jar"

    # Enhanced Java startup with better memory management
    java \
        --add-opens java.desktop/javax.swing=ALL-UNNAMED \
        --add-opens java.desktop/javax.swing.plaf=ALL-UNNAMED \
        --add-opens java.base/java.lang.reflect=ALL-UNNAMED \
        --add-opens java.desktop/java.awt=ALL-UNNAMED \
        --add-opens java.desktop/sun.awt=ALL-UNNAMED \
        --add-exports java.desktop/sun.awt.X11=ALL-UNNAMED \
        -cp "IBC.jar:$IBG_JARS:$IBG_INSTALL4J" \
        -Dtwslaunch.autoupdate.serviceImpl=com.ib.tws.twslaunch.install4j.Install4jAutoUpdateService \
        -Dchannel=stable \
        -Dexe4j.isInstall4j=true \
        -Dinstall4jType=standalone \
        -DjtsConfigDir="$TWS_PATH" \
        -Djava.awt.headless=false \
        -Dswing.volatileImageBufferEnabled=false \
        -Dswing.bufferPerWindow=false \
        -Xmx4096m \
        -Xms1024m \
        -XX:+UseG1GC \
        -XX:MaxGCPauseMillis=200 \
        -XX:+UseStringDeduplication \
        -XX:+OptimizeStringConcat \
        -Djava.net.preferIPv4Stack=true \
        ibcalpha.ibc.IbcGateway "$CONFIG_FILE" paper "$@" \
        2>&1 | tee -a "$LOG_FILE" &

    local PID=$!
    echo "$PID" > "$PID_FILE"

    log "✅ IBC Gateway started with PID: $PID"

    # Start authentication helper in background
    /tmp/ib_auth_helper.sh &

    return $PID
}

# Health check and monitoring
health_check() {
    log "🏥 Performing health checks..."

    local timeout=300  # 5 minutes
    local check_interval=10

    while [ $timeout -gt 0 ]; do
        # Check if process is running
        if ! pgrep -f "ibcalpha.ibc.IbcGateway" >/dev/null; then
            log "❌ IB Gateway process died"
            return 1
        fi

        # Check API port
        if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
            log "✅ API port 4002 is responsive"
            return 0
        fi

        log "⏳ Waiting for API port to be responsive... (${timeout}s remaining)"
        sleep $check_interval
        ((timeout-=check_interval))
    done

    log "❌ Health check failed - API port not responsive within timeout"
    return 1
}

# Start monitoring daemon
start_monitoring() {
    log "📊 Starting permanent monitoring daemon..."

    cat > "/tmp/ib_gateway_monitor.sh" << 'EOF'
#!/bin/bash
# Permanent IB Gateway Monitor

MONITOR_INTERVAL=60  # Check every minute
API_PORT=4002
LOG_FILE="/home/davidsanker/platform/logs/ib-gateway/monitor.log"

while true; do
    # Check if API port is responsive
    if ! timeout 3 bash -c "echo '' | nc 127.0.0.1 $API_PORT" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] API port $API_PORT not responsive - checking process" >> "$LOG_FILE"

        # Check if process is running
        if ! pgrep -f "ibcalpha.ibc.IbcGateway" >/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] IB Gateway process died - restarting" >> "$LOG_FILE"
            # Restart script
            /home/davidsanker/platform/bin/permanent_ib_gateway.sh restart &
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Process running but API not responding - may need authentication" >> "$LOG_FILE"
        fi
    fi

    sleep $MONITOR_INTERVAL
done
EOF

    chmod +x "/tmp/ib_gateway_monitor.sh"

    # Start monitor in background
    /tmp/ib_gateway_monitor.sh &
    MONITOR_PID=$!

    log "✅ Monitoring daemon started with PID: $MONITOR_PID"
    echo "$MONITOR_PID" > "/tmp/ib_gateway_monitor.pid"
}

# Main execution
main() {
    local action="${1:-start}"

    case "$action" in
        "start")
            log "🚀 Starting Enhanced IB Gateway (Permanent Solution)"

            check_vnc
            prepare_x11
            cleanup_existing
            setup_gui_automation

            local pid
            pid=$(start_enhanced_ibc)

            if health_check; then
                log "✅ IB Gateway started successfully and is healthy"
                start_monitoring
                log "🎉 Enhanced IB Gateway is now running permanently"
                log "📊 API Port: 4002"
                log "🖥️  VNC Display: $VNC_DISPLAY"
                log "📝 Logs: $LOG_FILE"
            else
                log "❌ IB Gateway failed health checks"
                exit 1
            fi
            ;;

        "stop")
            log "🛑 Stopping Enhanced IB Gateway..."

            # Kill monitor
            if [ -f "/tmp/ib_gateway_monitor.pid" ]; then
                kill "$(cat /tmp/ib_gateway_monitor.pid)" || true
                rm -f "/tmp/ib_gateway_monitor.pid"
            fi

            # Kill main process
            cleanup_existing
            rm -f "$PID_FILE"

            log "✅ Enhanced IB Gateway stopped"
            ;;

        "restart")
            log "🔄 Restarting Enhanced IB Gateway..."
            "$0" stop
            sleep 5
            "$0" start
            ;;

        "status")
            if pgrep -f "ibcalpha.ibc.IbcGateway" >/dev/null; then
                log "✅ IB Gateway is running"
                if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
                    log "✅ API port 4002 is responsive"
                else
                    log "⚠️  API port 4002 is not responsive"
                fi
            else
                log "❌ IB Gateway is not running"
            fi
            ;;

        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"