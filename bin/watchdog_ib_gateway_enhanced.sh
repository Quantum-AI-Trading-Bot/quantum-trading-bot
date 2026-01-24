#!/bin/bash
# Enhanced IB Gateway Watchdog with Multi-Layer Checks and Alerting
# Implements Priority 3 hardening measures

set -e

# Configuration
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
CHECK_INTERVAL=30  # seconds
BACKOFF_BASE=30    # base backoff in seconds
BACKOFF_MAX=300    # max backoff in seconds
LOCKFILE="/tmp/ib_gateway_watchdog_enhanced.lock"
MANUAL_LOGIN_FLAG="/home/davidsanker/platform/IB_GATEWAY_MANUAL_LOGIN_REQUIRED"
MAX_FAILURES=3
ALERT_EMAIL="${ALERT_EMAIL:-}"  # Set via environment or leave empty
FAILURE_COUNT_FILE="/tmp/gateway_failure_count"
INCIDENT_DIR="/home/davidsanker/platform/logs/incidents"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$INCIDENT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/watchdog_enhanced.log"
}

# Multi-layer gateway check
check_gateway() {
    local failures=0
    
    # Layer 1: Process check
    if ! pgrep -f "ibgateway|java.*gateway" > /dev/null 2>&1; then
        log "${RED}✗ Layer 1 FAIL: Gateway process not running${NC}"
        failures=$((failures + 1))
    else
        log "${GREEN}✓ Layer 1 PASS: Gateway process running${NC}"
    fi
    
    # Layer 2: Port check
    if ! timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
        log "${RED}✗ Layer 2 FAIL: Port 4002 not listening${NC}"
        failures=$((failures + 1))
    else
        log "${GREEN}✓ Layer 2 PASS: Port 4002 listening${NC}"
    fi
    
    # Layer 3: API handshake test
    if ! /home/davidsanker/platform/bin/validate_ib_gateway.sh paper > /dev/null 2>&1; then
        log "${RED}✗ Layer 3 FAIL: API handshake failed${NC}"
        failures=$((failures + 1))
    else
        log "${GREEN}✓ Layer 3 PASS: API handshake successful${NC}"
    fi
    
    return $failures
}

# Send alert
send_alert() {
    local subject="IB Gateway Watchdog Alert: $1"
    local message="$2"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local alert_file="$INCIDENT_DIR/alert_${timestamp}.txt"
    
    # Write alert to file
    cat > "$alert_file" << ALERTEOF
================================================================================
IB GATEWAY WATCHDOG ALERT
================================================================================
Timestamp: $(date)
Subject: $subject
Message: $message
================================================================================
System: $(hostname)
Uptime: $(uptime)
Gateway Process: $(pgrep -f ibgateway > /dev/null && echo "RUNNING" || echo "NOT RUNNING")
Port 4002: $(ss -ltnp | grep :4002 > /dev/null && echo "OPEN" || echo "CLOSED")
================================================================================
ALERTEOF
    
    log "${RED}ALERT WRITTEN: $alert_file${NC}"
    
    # Send email if configured
    if [ -n "$ALERT_EMAIL" ] && command -v mail > /dev/null 2>&1; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
        log "${GREEN}Email sent to: $ALERT_EMAIL${NC}"
    else
        log "${YELLOW}ALERT (email not configured or 'mail' command unavailable)${NC}"
    fi
}

# Stop bot services safely
stop_bots() {
    log "${YELLOW}Stopping bot services due to gateway failure${NC}"
    
    # Stop trading bot services
    systemctl stop trading-bot.service 2>/dev/null || true
    systemctl stop trading-bot-quantum.service 2>/dev/null || true
    
    log "${GREEN}Bot services stopped${NC}"
}

# Cleanup on exit
cleanup() {
    log "Watchdog stopping, removing lockfile"
    rm -f "$LOCKFILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Check for lockfile
if [ -f "$LOCKFILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCKFILE"))))
    if [ $LOCK_AGE -lt 600 ]; then
        log "${YELLOW}Watchdog already running (lockfile exists, age ${LOCK_AGE}s)${NC}"
        exit 1
    else
        log "${YELLOW}Stale lockfile found (age ${LOCK_AGE}s), removing${NC}"
        rm -f "$LOCKFILE"
    fi
fi

# Create lockfile
echo $$ > "$LOCKFILE"
log "=== Enhanced IB Gateway Watchdog Started (PID: $$) ==="

# Initialize failure count
FAILURE_COUNT=$(cat "$FAILURE_COUNT_FILE" 2>/dev/null || echo "0")

# Main watchdog loop
while true; do
    # Check for emergency stop
    if [ -f "/home/davidsanker/EMERGENCY_STOP" ]; then
        log "${RED}EMERGENCY_STOP detected, watchdog paused${NC}"
        sleep 60
        continue
    fi
    
    # Run multi-layer check
    check_gateway
    CHECK_RESULT=$?
    
    if [ $CHECK_RESULT -eq 0 ]; then
        # All checks passed
        if [ $FAILURE_COUNT -gt 0 ]; then
            log "${GREEN}✓ Gateway recovered after $FAILURE_COUNT failure cycles${NC}"
            send_alert "Gateway Recovered" "Gateway is now healthy after $FAILURE_COUNT failure cycles. All layers passing."
            echo "0" > "$FAILURE_COUNT_FILE"
            FAILURE_COUNT=0
        else
            log "${GREEN}✓ Gateway healthy (all 3 layers passing)${NC}"
        fi
    else
        # One or more layers failed
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        echo "$FAILURE_COUNT" > "$FAILURE_COUNT_FILE"
        
        log "${RED}✗ Gateway unhealthy: $CHECK_RESULT/3 layers failed (failure cycle #$FAILURE_COUNT)${NC}"
        
        # Check if we've hit max failures
        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            log "${RED}CRITICAL: Max failures ($MAX_FAILURES) reached${NC}"
            
            # Stop bots to prevent operation without gateway
            stop_bots
            
            # Send alert
            send_alert "Gateway Critical Failure" "Gateway has failed $MAX_FAILURES consecutive health checks. Bot services have been stopped. Manual intervention required."
            
            # Check if manual login already flagged
            if [ ! -f "$MANUAL_LOGIN_FLAG" ]; then
                touch "$MANUAL_LOGIN_FLAG"
                
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "${YELLOW}  CRITICAL: MANUAL INTERVENTION REQUIRED${NC}"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "Watchdog has stopped bot services after $FAILURE_COUNT failure cycles"
                log ""
                log "IMMEDIATE ACTION REQUIRED:"
                log "1. Connect via VNC: vncviewer 35.232.64.211:5901"
                log "   or noVNC: http://35.232.64.211:6080/vnc.html"
                log "2. Diagnose and fix IB Gateway"
                log "3. Once gateway is healthy, remove manual flag:"
                log "   rm $MANUAL_LOGIN_FLAG"
                log "4. Restart bot services:"
                log "   systemctl start trading-bot.service"
                log ""
                log "Alert written to: $INCIDENT_DIR/"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            fi
            
            # Reset failure count and wait longer
            echo "0" > "$FAILURE_COUNT_FILE"
            FAILURE_COUNT=0
            sleep 300  # Wait 5 minutes
            continue
        fi
        
        # Attempt recovery if not at max failures yet
        log "Attempting recovery in ${BACKOFF_BASE}s..."
        sleep $BACKOFF_BASE
        
        # Try restarting gateway service
        log "Attempting systemctl restart ibgateway.service..."
        systemctl restart ibgateway.service 2>&1 | tee -a "$LOG_DIR/watchdog_enhanced.log"
        
        # Wait for gateway to stabilize
        sleep 30
    fi
    
    # Sleep until next check
    sleep $CHECK_INTERVAL
done
