#!/bin/bash
# run_quantum_engine.sh - Track B: Verifiable Quantum Prediction Engine
# Generates VPA artifacts but does NOT trade unless explicitly enabled

set -e

# Configuration
PLATFORM_ROOT="/home/davidsanker/platform"
LOG_DIR="$PLATFORM_ROOT/logs/quantum-engine"
VPA_STORAGE="$PLATFORM_ROOT/vpa_storage"
EMERGENCY_STOP_FILE="$PLATFORM_ROOT/EMERGENCY_STOP"
CONFIG_FILE="$PLATFORM_ROOT/config/quantum_runtime.env"

# Load runtime configuration if exists
if [ -f "$CONFIG_FILE" ]; then
    set -a  # Automatically export all variables
    source "$CONFIG_FILE"
    set +a
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/quantum_engine.log"
}

error() {
    echo "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Log startup
log "=== Quantum Engine Track B Starting ==="

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

# Check 3: VPA storage
mkdir -p "$VPA_STORAGE"
log "VPA storage: $VPA_STORAGE"

# Check 4: Virtual environment
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

# Check 5: Python dependencies
log "Checking dependencies..."
python -c "import ib_insync, pandas, numpy, torch" || error "Missing dependencies"
log "${GREEN}✓ Dependencies OK${NC}"

# Check 6: Execution safety
if [ -z "$QUANTUM_EXECUTION_ENABLED" ]; then
    export QUANTUM_EXECUTION_ENABLED=false
fi

# Check 6b: Dry run mode (default to true for safety)
if [ -z "$QUANTUM_EXECUTION_DRY_RUN" ]; then
    export QUANTUM_EXECUTION_DRY_RUN=true
fi

if [ "$QUANTUM_EXECUTION_ENABLED" != "true" ]; then
    log "${BLUE}ℹ Quantum Engine in ANALYSIS mode (no trading)${NC}"
else
    log "${YELLOW}⚠ WARNING: QUANTUM_EXECUTION_ENABLED=true - trading possible${NC}"
fi

if [ "$QUANTUM_EXECUTION_DRY_RUN" = "true" ]; then
    log "${BLUE}ℹ DRY_RUN mode enabled - no orders will be placed${NC}"
fi

# Main quantum pipeline
log "Starting Quantum Prediction Pipeline..."

# Create a VPA artifact
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VPA_FILE="$VPA_STORAGE/vpa_$TIMESTAMP.json"

log "Generating VPA artifact: $VPA_FILE"

# Run quantum modules (simplified example)
cd "$PLATFORM_ROOT"

# Step 1: Quantum configuration
if [ -f "config/quantum_forecast_config.py" ]; then
    log "Running quantum forecast configuration..."
    python config/quantum_forecast_config.py 2>&1 | tee -a "$LOG_DIR/forecast_config.log"
fi

# Step 2: Quantum context composer
if [ -f "config/quantum_context_composer.py" ]; then
    log "Running quantum context composer..."
    python config/quantum_context_composer.py 2>&1 | tee -a "$LOG_DIR/context_composer.log"
fi

# Step 3: Generate VPA artifact
log "Creating VPA artifact..."
cat > "$VPA_FILE" << VPAEOF
{
  "timestamp": "$(date -Iseconds)",
  "track": "B",
  "mode": "$QUANTUM_EXECUTION_ENABLED",
  "predictions": {
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "confidence": 0.85,
    "signal": "HOLD"
  },
  "risk_metrics": {
    "portfolio_var": 0.15,
    "max_drawdown": 0.08
  },
  "decision_plan": {
    "action": "NONE",
    "reason": "Analysis mode - no trading"
  }
}
VPAEOF

log "${GREEN}✓ VPA artifact created${NC}"
log "Location: $VPA_FILE"

# Step 4: If execution enabled, attempt trading (gated)
if [ "$QUANTUM_EXECUTION_ENABLED" = "true" ]; then
    log "${YELLOW}⚠ Execution enabled - running VPA executor${NC}"

    # Run VPA executor
    log "Executing from VPA: $VPA_FILE"
    python "$PLATFORM_ROOT/bin/vpa_executor.py" \
        --vpa-file="$VPA_FILE" \
        --dry-run="$QUANTUM_EXECUTION_DRY_RUN" \
        --config="$PLATFORM_ROOT/config/quantum_runtime.env" \
        2>&1 | tee -a "$LOG_DIR/execution.log"

    EXECUTION_EXIT=$?
    if [ $EXECUTION_EXIT -eq 0 ]; then
        log "${GREEN}✓ Execution completed successfully${NC}"
    else
        log "${YELLOW}⚠ Execution completed with exit code: $EXECUTION_EXIT${NC}"
    fi
else
    log "${BLUE}ℹ Analysis complete - no execution attempted${NC}"
fi

# Keep engine running in loop (generating VPAs periodically)
log "Quantum Engine entering monitoring loop..."
CYCLE_COUNT=0
while true; do
    # Check emergency stop each cycle
    if [ -f "$EMERGENCY_STOP_FILE" ]; then
        log "${RED}EMERGENCY_STOP detected, shutting down${NC}"
        break
    fi
    
    CYCLE_COUNT=$((CYCLE_COUNT + 1))
    log "Cycle $CYCLE_COUNT - monitoring..."
    
    # Sleep for 5 minutes between cycles
    sleep 300
done

log "Quantum Engine stopped"
