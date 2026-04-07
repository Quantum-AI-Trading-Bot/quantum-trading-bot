#!/bin/bash
# auto_reconnect_watchdog.sh - Continuous 24/7 IB Gateway Auto-Reconnect
# Ensures trading bot is ALWAYS online with real-time monitoring and recovery
# Runs continuously as a daemon with 30-second check intervals

set -e

# Configuration
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
CHECK_INTERVAL=30  # Check every 30 seconds
MAX_FAILURES=3     # After 3 failures, require manual intervention
RESTART_DELAY=60   # Wait 60s between restart attempts
LOCKFILE="/tmp/auto_reconnect_watchdog.lock"
PIDFILE="/tmp/auto_reconnect_watchdog.pid"
EMERGENCY_STOP="/home/davidsanker/platform/EMERGENCY_STOP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    local level="$1"
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo -e "$msg" | tee -a "$LOG_DIR/auto_reconnect.log"
}

# Cleanup function
cleanup() {
    log "INFO" "Watchdog stopping, cleaning up lock files"
    rm -f "$LOCKFILE"
    rm -f "$PIDFILE"
    exit 0
}

# Signal handlers
trap cleanup SIGTERM SIGINT

# Check if already running
if [ -f "$LOCKFILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCKFILE")))
    if [ $LOCK_AGE -lt 300 ]; then  # Lock file less than 5 minutes old
        log "WARN" "Watchdog already running (lockfile age: ${LOCK_AGE}s)"
        exit 1
    else
        log "WARN" "Removing stale lockfile (age: ${LOCK_AGE}s)"
        rm -f "$LOCKFILE"
    fi
fi

# Create lock and PID files
echo $$ > "$PIDFILE"
echo $$ > "$LOCKFILE"

log "INFO" "═══════════════════════════════════════════════════════════════"
log "INFO" "🚀 AUTO-RECONNECT WATCHDOG STARTING (PID: $$)"
log "INFO" "═══════════════════════════════════════════════════════════════"
log "INFO" "Check Interval: ${CHECK_INTERVAL}s | Max Failures: ${MAX_FAILURES}"

# Track failures
failure_count=0
last_restart_time=0

# Main monitoring loop
while true; do
    # Check for emergency stop
    if [ -f "$EMERGENCY_STOP" ]; then
        log "WARN" "⚠️  EMERGENCY_STOP detected - monitoring paused"
        sleep 60
        continue
    fi

    # Get current time
    current_time=$(date +%s)

    # Check 1: IB Gateway Process
    if ! pgrep -f "ibgateway|IbcGateway" > /dev/null 2>&1; then
        failure_count=$((failure_count + 1))
        log "ERROR" "❌ IB Gateway process not running (failure #$failure_count/$MAX_FAILURES)"

        if [ $failure_count -ge $MAX_FAILURES ]; then
            log "ERROR" "🚨 Too many failures! Manual intervention required"
            log "ERROR" "Check logs: $LOG_DIR/auto_reconnect.log"
            # Email alert DISABLED
            log "ERROR" "[EMAIL DISABLED] Would have sent: IB Gateway failed $MAX_FAILURES times - Manual intervention required"
            sleep 300
            continue
        fi

        # Attempt restart
        if [ $((current_time - last_restart_time)) -gt $RESTART_DELAY ]; then
            log "INFO" "🔄 Attempting to restart IB Gateway..."
            last_restart_time=$current_time

            # Start IB Gateway using IBC
            /home/davidsanker/IBC/gatewaystart.sh > "$LOG_DIR/auto_restart.log" 2>&1 &

            # Wait for startup
            sleep 30

            # Verify it started
            if pgrep -f "ibgateway|IbcGateway" > /dev/null 2>&1; then
                log "INFO" "✅ IB Gateway restarted successfully"
                failure_count=0
            else
                log "ERROR" "❌ Failed to restart IB Gateway"
            fi
        else
            log "INFO" "⏳ Waiting before next restart attempt"
        fi

        sleep $CHECK_INTERVAL
        continue
    fi

    # Check 2: API Port 4002 (using Python for reliable testing)
    if ! timeout 5 python3 -c "import socket; s = socket.socket(); s.settimeout(3); s.connect(('127.0.0.1', 4002)); s.close()" > /dev/null 2>&1; then
        failure_count=$((failure_count + 1))
        log "ERROR" "❌ API Port 4002 not accessible (failure #$failure_count/$MAX_FAILURES)"

        if [ $failure_count -ge $MAX_FAILURES ]; then
            log "ERROR" "🚨 API not responding after $MAX_FAILURES attempts - Manual intervention required"
            # Email alert DISABLED
            log "ERROR" "[EMAIL DISABLED] Would have sent: IB Gateway API not responding - Manual intervention required"
            sleep 300
            continue
        fi

        # Try to restart gateway
        if [ $((current_time - last_restart_time)) -gt $RESTART_DELAY ]; then
            log "INFO" "🔄 Restarting IB Gateway to restore API..."
            last_restart_time=$current_time

            # Kill existing gateway
            pkill -f "ibgateway|IbcGateway" || true
            sleep 10

            # Start again
            /home/davidsanker/IBC/gatewaystart.sh > "$LOG_DIR/auto_restart.log" 2>&1 &

            # Wait for startup
            sleep 45

            # Verify API is accessible
            if timeout 5 python3 -c "import socket; s = socket.socket(); s.settimeout(3); s.connect(('127.0.0.1', 4002)); s.close()" > /dev/null 2>&1; then
                log "INFO" "✅ API restored successfully"
                failure_count=0
            else
                log "ERROR" "❌ API still not accessible after restart"
            fi
        fi

        sleep $CHECK_INTERVAL
        continue
    fi

    # Check 3: Trading Bot Process
    if ! pgrep -f "quantum_trading_bot.py" > /dev/null 2>&1; then
        log "WARN" "⚠️  Trading bot not running, attempting restart..."

        # Start trading bot
        cd /home/davidsanker/quantum-trading-bot-new
        PYTHONPATH=/home/davidsanker/quantum-trading-bot-new/src:$PYTHONPATH \
        /home/davidsanker/venv/bin/python3 bin/quantum_trading_bot.py \
        > /home/davidsanker/logs/trading_bot.log 2>&1 &

        sleep 10

        if pgrep -f "quantum_trading_bot.py" > /dev/null 2>&1; then
            log "INFO" "✅ Trading bot restarted successfully"
        else
            log "ERROR" "❌ Failed to restart trading bot"
        fi
    fi

    # All checks passed
    if [ $failure_count -gt 0 ]; then
        log "INFO" "✅ System recovered after $failure_count failures"
        failure_count=0
    fi

    # Log healthy status (every 10 minutes)
    if [ $((current_time % 600)) -lt $CHECK_INTERVAL ]; then
        log "INFO" "✅ All systems operational - Gateway running, API accessible, Bot active"
    fi

    # Sleep until next check
    sleep $CHECK_INTERVAL
done
