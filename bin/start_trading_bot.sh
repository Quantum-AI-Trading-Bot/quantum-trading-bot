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
python3 -c "import torch, ib_insync, qiskit" || die "Required Python packages missing"
log "   ✓ Python environment OK"

# 3. Pre-flight: Model files
log "[3/5] Checking quantum models..."
MODEL_DIR="/home/davidsanker/brain-data/apps/investor/quantum_models"
test -d "${MODEL_DIR}" || die "Model directory missing: ${MODEL_DIR}"
test -f "${MODEL_DIR}/quantum_lstm_forecaster.pkl" || log "   WARNING: LSTM model not found (will train from scratch)"
log "   ✓ Model directory exists"

# 4. Pre-flight: Trading bot code integrity
log "[4/5] Validating trading bot code..."
BOT_SCRIPT="/mnt/investor/projects/Investor/quantum_enhanced_trading_bot.py"
test -f "${BOT_SCRIPT}" || die "Trading bot script missing: ${BOT_SCRIPT}"

# Check for known bugs (post-patch verification)
if grep -q "order = MarketOrder(ib_action, quantity)" "${BOT_SCRIPT}" && \
   grep -A2 "order = MarketOrder(ib_action, quantity)" "${BOT_SCRIPT}" | grep -q "ib_action = 'BUY'"; then
    die "CRITICAL: Trading bot still has order mapping bug (line ~597). Apply patches first!"
fi

if ! grep -q "^import json" "${BOT_SCRIPT}"; then
    die "CRITICAL: Trading bot missing 'import json' statement. Apply patches first!"
fi

log "   ✓ Code integrity checks passed"

# 5. Start trading bot
log "[5/5] Starting trading bot..."
cd /mnt/investor/projects/Investor

# Run bot with unbuffered output
exec python3 -u quantum_enhanced_trading_bot.py 2>&1 | tee -a "${LOG_FILE}"
