#!/bin/bash
# recover_ib_gateway.sh - Recover IB Gateway to healthy state
# This script starts/restarts IB Gateway and waits for API to be ready

set -e

# Configuration
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
MANUAL_LOGIN_FLAG="/home/davidsanker/platform/IB_GATEWAY_MANUAL_LOGIN_REQUIRED"
MAX_WAIT=120  # Maximum seconds to wait for API port
PORT_CHECK_INTERVAL=5  # Check every 5 seconds

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/recovery.log"
}

# Remove manual login flag if it exists
rm -f "$MANUAL_LOGIN_FLAG"

log "=== IB Gateway Recovery Started ==="

# Step 1: Check if gateway/TWS process is running
if pgrep -f "ibgateway|GWClient|install4j|tws" > /dev/null 2>&1; then
    log "${YELLOW}Gateway/TWS process already running, checking API...${NC}"
else
    log "Starting IB API (preferring TWS)..."

    # Try to start using existing start script (prefer TWS over Gateway)
    if [ -f "/home/davidsanker/IBC/twsstart.sh" ]; then
        log "Using IBC twsstart.sh (TWS)"
        /home/davidsanker/IBC/twsstart.sh >> "$LOG_DIR/start.log" 2>&1 &
    elif [ -f "/home/davidsanker/platform/bin/start_ib_gateway.sh" ]; then
        log "Using existing start_ib_gateway.sh"
        /home/davidsanker/platform/bin/start_ib_gateway.sh >> "$LOG_DIR/start.log" 2>&1 &
    elif [ -f "/home/davidsanker/IBC/gatewaystart.sh" ]; then
        log "Using IBC gatewaystart.sh (Gateway)"
        /home/davidsanker/IBC/gatewaystart.sh >> "$LOG_DIR/start.log" 2>&1 &
    else
        log "${RED}ERROR: No gateway/TWS start script found${NC}"
        exit 1
    fi

    log "Waiting for process to start..."
    sleep 10
fi

# Step 2: Wait for API port to be listening
log "Waiting for API port 4002 to be listening (max ${MAX_WAIT}s)..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" > /dev/null 2>&1; then
        log "${GREEN}✓ API port 4002 is listening${NC}"
        
        # Step 3: Try handshake to verify API is ready
        log "Verifying API handshake..."
        HANDSHAKE_RESULT=$(/home/davidsanker/platform/bin/validate_ib_gateway.sh 2>&1)
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            log "${GREEN}✓ Gateway fully operational${NC}"
            exit 0
        elif [ $EXIT_CODE -eq 4 ]; then
            log "${YELLOW}⚠ Port listening but authentication required${NC}"
            log "Setting manual login flag"
            touch "$MANUAL_LOGIN_FLAG"
            log ""
            log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            log "${YELLOW}  MANUAL LOGIN REQUIRED${NC}"
            log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            log "1. Connect via VNC: vncviewer 35.232.64.211:5901"
            log "   or via noVNC: http://35.232.64.211:6080/vnc.html"
            log "2. Complete IB Gateway authentication (2FA)"
            log "3. After login, API port 4002 should become active"
            log "4. Run: /home/davidsanker/platform/bin/validate_ib_gateway.sh"
            log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            exit 4
        else
            log "${RED}✗ Gateway validation failed (exit code $EXIT_CODE)${NC}"
            log "$HANDSHAKE_RESULT"
            exit 1
        fi
    fi
    
    sleep $PORT_CHECK_INTERVAL
    WAITED=$((WAITED + PORT_CHECK_INTERVAL))
    echo -n "."
done

log ""
log "${RED}✗ Timeout waiting for API port${NC}"
log "Gateway process may need manual authentication"
exit 3
