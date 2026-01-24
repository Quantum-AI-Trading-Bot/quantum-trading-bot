#!/bin/bash
# start_dual_track_stack.sh - Main entry point for dual-track system
# Usage: start_dual_track_stack.sh [mvp|quantum] [paper|live]

set -e

# Configuration
PLATFORM_ROOT="/home/davidsanker/platform"
TRACK="${1:-mvp}"  # Default to MVP
MODE="${2:-paper}"  # Default to paper

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Banner
echo "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo "${BLUE}║     Quantum AI Trading Bot - Dual-Track System            ║${NC}"
echo "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
log "Starting stack: Track=$TRACK, Mode=$MODE"

# Validate inputs
if [ "$TRACK" != "mvp" ] && [ "$TRACK" != "quantum" ]; then
    error "Invalid track: $TRACK (must be 'mvp' or 'quantum')"
fi

if [ "$MODE" != "paper" ] && [ "$MODE" != "live" ]; then
    error "Invalid mode: $MODE (must be 'paper' or 'live')"
fi

# Step 1: Validate IB Gateway is ready (using ib_insync handshake)
log "Step 1: Validating IB Gateway..."
if ! "$PLATFORM_ROOT/bin/validate_ib_gateway.sh"; then
    VALIDATION_EXIT=$?

    if [ $VALIDATION_EXIT -eq 4 ]; then
        log "${YELLOW}⚠ Gateway requires authentication${NC}"
        echo ""
        echo "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo "${YELLOW}  MANUAL LOGIN REQUIRED${NC}"
        echo "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo "1. Connect via VNC: vncviewer 35.232.64.211:5901"
        echo "   or noVNC: http://35.232.64.211:6080/vnc.html"
        echo "2. Complete IB Gateway authentication"
        echo "3. Run: $0 $TRACK $MODE"
        echo ""
        exit 4
    else
        error "IB Gateway not ready (exit code $VALIDATION_EXIT)"
    fi
fi
log "${GREEN}✓ IB Gateway ready${NC}"

# Step 2: Check kill-switch (safety)
log "Step 2: Checking kill-switch..."
if [ -f "$PLATFORM_ROOT/EMERGENCY_STOP" ]; then
    error "EMERGENCY_STOP file exists, cannot start"
fi
log "${GREEN}✓ No emergency stop active${NC}"

# Step 3: Verify paper trading mode enforced
log "Step 3: Verifying paper trading mode..."
if grep -q "TradingMode=live" /home/davidsanker/IBC/config.ini 2>/dev/null; then
    error "Live trading mode detected in IBC config (not allowed)"
fi
log "${GREEN}✓ Paper trading mode enforced${NC}"

# Step 4: Optional watchdog status (informational, non-blocking)
if ! systemctl --user is-active --quiet ibgateway-watchdog.service 2>/dev/null; then
    log "${YELLOW}⚠ Warning: Watchdog not running (recommended but not required)${NC}"
    log "  To start: systemctl --user start ibgateway-watchdog.service"
else
    log "${GREEN}✓ Watchdog running${NC}"
fi

# Step 5: Set environment variables
export TRADING_MODE="$MODE"
export TRADING_ENABLED=false  # Default to safe mode
export QUANTUM_EXECUTION_ENABLED=false

# Step 6: Start the selected track
log "Step 6: Starting Track $TRACK..."

case "$TRACK" in
    mvp)
        log "Starting MVP Bot (Track A)..."
        exec "$PLATFORM_ROOT/bin/run_mvp_bot.sh"
        ;;
    
    quantum)
        log "Starting Quantum Engine (Track B)..."
        exec "$PLATFORM_ROOT/bin/run_quantum_engine.sh"
        ;;
    
    *)
        error "Unknown track: $TRACK"
        ;;
esac
