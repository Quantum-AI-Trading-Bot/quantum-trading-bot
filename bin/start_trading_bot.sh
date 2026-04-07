#!/bin/bash
set -euo pipefail

# ============================================================================
# Trading Bot Startup Script with Pre-Flight Checks
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/trading-bot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/startup_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

die() {
    log "ERROR: $*"
    exit 1
}

log "=========================================="
log "Trading Bot Startup - ${TIMESTAMP}"
log "=========================================="

# 1. Pre-flight: IB Gateway API
log "[1/5] Checking IB Gateway API..."
nc -z 127.0.0.1 4002 || die "IB Gateway API not available on port 4002"
log "   ✓ Port 4002 reachable"

# 2. Pre-flight: Python environment
log "[2/5] Checking Python environment..."
test -d ~/venv || die "Virtual environment missing at ~/venv"
source ~/venv/bin/activate
python3 -c "import ib_insync, pandas, numpy, yfinance" || die "Required Python packages missing"
log "   ✓ Python environment OK"

# 2b. Load runtime configuration
log "[2b/5] Loading runtime configuration..."
RUNTIME_ENV="/home/davidsanker/platform/config/quantum_runtime.env"
if [[ -f "${RUNTIME_ENV}" ]]; then
    set -a  # Export all variables
    source "${RUNTIME_ENV}"
    set +a
    log "   ✓ Loaded ${RUNTIME_ENV}"
    log "   QUANTUM_EXECUTION_DRY_RUN=${QUANTUM_EXECUTION_DRY_RUN:-not set}"
    log "   QUANTUM_EXECUTION_ENABLED=${QUANTUM_EXECUTION_ENABLED:-not set}"
    log "   PAPER_EXECUTION_MODE=${PAPER_EXECUTION_MODE:-not set}"
else
    die "Runtime configuration missing: ${RUNTIME_ENV}"
fi

# 3. Pre-flight: Model files
log "[3/5] Checking quantum models..."
MODEL_DIR="/home/davidsanker/brain-data/apps/investor/quantum_models"
test -d "${MODEL_DIR}" || die "Model directory missing: ${MODEL_DIR}"
test -f "${MODEL_DIR}/quantum_lstm_forecaster.pkl" || log "   WARNING: LSTM model not found (will train from scratch)"
log "   ✓ Model directory exists"

# 4. Pre-flight: Trading bot script exists
log "[4/5] Validating trading bot code..."
BOT_SCRIPT="/home/davidsanker/platform/bin/quantum_enhanced_trading_bot.py"
test -f "${BOT_SCRIPT}" || die "Trading bot script missing: ${BOT_SCRIPT}"
log "   ✓ Bot script exists"

# 5. Start trading bot
log "[5/5] Starting trading bot..."
cd /home/davidsanker/platform

# Run bot with unbuffered output
exec python3 -u "${BOT_SCRIPT}" 2>&1 | tee -a "${LOG_FILE}"
