#!/bin/bash
# run_mvp_bot.sh - Track A: MVP Paper Trading Bot
# Safe, minimal trading bot with strict guardrails

set -e

# Configuration
PLATFORM_ROOT="/home/davidsanker/platform"
LOG_DIR="$PLATFORM_ROOT/logs/trading-bot"
EMERGENCY_STOP_FILE="$PLATFORM_ROOT/EMERGENCY_STOP"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/mvp_bot.log"
}

error() {
    echo "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Log startup
log "=== MVP Bot Track A Starting ==="

# Check 1: Emergency stop
if [ -f "$EMERGENCY_STOP_FILE" ]; then
    error "EMERGENCY_STOP file exists, cannot start"
fi

# Check 2: IB Gateway validation
log "Validating IB Gateway..."
if ! "$PLATFORM_ROOT/bin/validate_ib_gateway.sh"; then
    error "IB Gateway not ready (exit code $?)"
fi
log "${GREEN}✓ IB Gateway ready${NC}"

# Check 3: Environment setup
if [ -z "$TRADING_MODE" ]; then
    export TRADING_MODE=paper
fi

if [ -z "$ALLOW_LIVE" ]; then
    export ALLOW_LIVE=false
fi

# Check 4: Paper/Live guardrails
if [ "$TRADING_MODE" = "live" ] && [ "$ALLOW_LIVE" != "true" ]; then
    error "LIVE trading mode requested but not allowed. Set ALLOW_LIVE=true to override."
fi

if [ "$TRADING_MODE" = "live" ]; then
    log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    log "${YELLOW}  WARNING: LIVE TRADING MODE${NC}"
    log "${YELLOW}  REAL MONEY AT RISK${NC}"
    log "${YELLOW}═══════════════════════════════════════════════════════${NC}"
fi

# Check 5: Virtual environment
VENV_DIRS="$HOME/trading_bot_venv $HOME/venv"
VENV=""
for dir in $VENV_DIRS; do
    if [ -d "$dir" ]; then
        VENV="$dir"
        break
    fi
done

if [ -z "$VENV" ]; then
    error "No virtual environment found"
fi

log "Using venv: $VENV"
source "$VENV/bin/activate"

# Check 6: Python dependencies
log "Checking dependencies..."
python -c "import ib_insync, pandas, numpy" || error "Missing dependencies"
log "${GREEN}✓ Dependencies OK${NC}"

# Check 7: Ensure trading is disabled by default
if [ -z "$TRADING_ENABLED" ]; then
    export TRADING_ENABLED=false
    log "${YELLOW}⚠ TRADING_ENABLED=false (signals only, no orders)${NC}"
fi

# Main bot execution
log "Starting MVP bot..."
log "Mode: $TRADING_MODE, Trading: $TRADING_ENABLED"

# Run the quantum trading bot with safe defaults
cd "$PLATFORM_ROOT"
exec python bin/quantum_trading_bot.py \
    --mode "$TRADING_MODE" \
    --trading-enabled "$TRADING_ENABLED" \
    --log-level INFO \
    2>&1 | tee -a "$LOG_DIR/mvp_bot_output.log"
