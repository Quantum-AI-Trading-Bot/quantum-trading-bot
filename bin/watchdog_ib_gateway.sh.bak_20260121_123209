#!/bin/bash
# watchdog_ib_gateway.sh - Monitor and recover IB Gateway
# Runs continuously, checks gateway health every 30s
# Lockfile-protected to prevent concurrent restarts

set -e

# Configuration
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
CHECK_INTERVAL=30  # seconds
BACKOFF_BASE=30    # base backoff in seconds
BACKOFF_MAX=300    # max backoff in seconds
LOCKFILE="/tmp/ib_gateway_watchdog.lock"
MANUAL_LOGIN_FLAG="/home/davidsanker/platform/IB_GATEWAY_MANUAL_LOGIN_REQUIRED"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/ib_watchdog.log"
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
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCKFILE")))
    if [ $LOCK_AGE -lt 600 ]; then  # Lock file less than 10 minutes old
        log "${YELLOW}Watchdog already running (lockfile exists, age ${LOCK_AGE}s)${NC}"
        exit 1
    else
        log "${YELLOW}Stale lockfile found (age ${LOCK_AGE}s), removing${NC}"
        rm -f "$LOCKFILE"
    fi
fi

# Create lockfile
echo $$ > "$LOCKFILE"
log "=== IB Gateway Watchdog Started (PID: $$) ==="

# Track consecutive failures and backoff
FAILURE_COUNT=0
BACKOFF_CURRENT=0

# Main watchdog loop
while true; do
    # Check for emergency stop
    if [ -f "/home/davidsanker/platform/EMERGENCY_STOP" ]; then
        log "${RED}EMERGENCY_STOP detected, watchdog paused${NC}"
        sleep 60
        continue
    fi
    
    # Run validation
    VALIDATOR_OUTPUT=$(/home/davidsanker/platform/bin/validate_ib_gateway.sh 2>&1)
    EXIT_CODE=$?
    
    case $EXIT_CODE in
        0)
            # All OK
            if [ $FAILURE_COUNT -gt 0 ]; then
                log "${GREEN}✓ Gateway recovered after $FAILURE_COUNT failures${NC}"
                FAILURE_COUNT=0
                BACKOFF_CURRENT=0
                rm -f "$MANUAL_LOGIN_FLAG"
            fi
            log "${GREEN}✓ Gateway healthy${NC}"
            ;;
        
        2|3)
            # Process not running (2) or port not listening (3)
            FAILURE_COUNT=$((FAILURE_COUNT + 1))
            log "${RED}✗ Gateway unhealthy (exit code $EXIT_CODE, failure #$FAILURE_COUNT)${NC}"
            
            # Check if we're already in manual login state
            if [ -f "$MANUAL_LOGIN_FLAG" ]; then
                log "${YELLOW}Manual login already flagged, not auto-restarting${NC}"
                log "Once login is complete via VNC, remove flag: rm $MANUAL_LOGIN_FLAG"
                sleep 60
                continue
            fi
            
            # Calculate backoff
            if [ $BACKOFF_CURRENT -eq 0 ]; then
                BACKOFF_CURRENT=$BACKOFF_BASE
            else
                BACKOFF_CURRENT=$((BACKOFF_CURRENT * 2))
                if [ $BACKOFF_CURRENT -gt $BACKOFF_MAX ]; then
                    BACKOFF_CURRENT=$BACKOFF_MAX
                fi
            fi
            
            # If we've failed 3+ times, give up and require manual login
            if [ $FAILURE_COUNT -ge 3 ]; then
                log "${YELLOW}Too many failures ($FAILURE_COUNT), requiring manual login${NC}"
                touch "$MANUAL_LOGIN_FLAG"
                
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "${YELLOW}  MANUAL INTERVENTION REQUIRED${NC}"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "Watchdog has paused auto-restart after $FAILURE_COUNT failures"
                log "Please:"
                log "1. Connect via VNC: vncviewer 35.232.64.211:5901"
                log "2. Complete IB Gateway authentication"
                log "3. Remove manual flag: rm $MANUAL_LOGIN_FLAG"
                log "4. Watchdog will resume monitoring"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                
                sleep 300  # Wait 5 minutes before checking again
                continue
            fi
            
            log "Attempting recovery in ${BACKOFF_CURRENT}s..."
            sleep $BACKOFF_CURRENT
            
            # Attempt recovery (in background to avoid blocking watchdog)
            log "Starting recovery..."
            /home/davidsanker/platform/bin/recover_ib_gateway.sh >> "$LOG_DIR/auto_recovery.log" 2>&1
            RECOVERY_EXIT=$?
            
            if [ $RECOVERY_EXIT -eq 0 ]; then
                log "${GREEN}Recovery successful${NC}"
            elif [ $RECOVERY_EXIT -eq 4 ]; then
                # Manual login required
                log "${YELLOW}Recovery indicates manual login required${NC}"
                touch "$MANUAL_LOGIN_FLAG"
            else
                log "${RED}Recovery failed (exit code $RECOVERY_EXIT)${NC}"
            fi
            ;;
        
        4)
            # Authentication required
            log "${YELLOW}⚠ Gateway requires authentication${NC}"
            touch "$MANUAL_LOGIN_FLAG"
            
            if [ ! -f "$LOG_DIR/manual_login_prompted" ]; then
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "${YELLOW}  MANUAL LOGIN REQUIRED${NC}"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                log "1. Connect via VNC: vncviewer 35.232.64.211:5901"
                log "   or noVNC: http://35.232.64.211:6080/vnc.html"
                log "2. Complete IB Gateway authentication (2FA)"
                log "3. After login, remove flag: rm $MANUAL_LOGIN_FLAG"
                log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
                touch "$LOG_DIR/manual_login_prompted"
            fi
            ;;
        
        *)
            # Unknown error
            log "${RED}✗ Unknown validator exit code: $EXIT_CODE${NC}"
            log "$VALIDATOR_OUTPUT"
            ;;
    esac
    
    # Sleep until next check
    sleep $CHECK_INTERVAL
done
