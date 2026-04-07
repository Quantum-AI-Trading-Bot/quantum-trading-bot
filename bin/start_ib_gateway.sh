#!/bin/bash
set -euo pipefail

# ============================================================================
# IB Gateway Startup Script with Health Checks
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
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
log "IB Gateway Startup - ${TIMESTAMP}"
log "=========================================="

# 1. Environment checks
log "[1/6] Checking environment..."
export DISPLAY="${DISPLAY:-:1}"
log "   DISPLAY=${DISPLAY}"
pgrep -x Xvfb > /dev/null || die "Xvfb not running on ${DISPLAY}"
test -f ~/IBC/config.ini || die "IBC config missing"
test -f ~/IBC/gatewaystart.sh || die "IBC gatewaystart.sh missing"
test -x ~/IBC/gatewaystart.sh || die "gatewaystart.sh not executable"
log "   ✓ Environment OK"

# 2. Kill any existing Gateway processes
log "[2/6] Cleaning up old processes..."
if pgrep -f "IbcGateway" > /dev/null; then
    log "   Found existing Gateway process, killing..."
    pkill -f "IbcGateway" || true
    sleep 5
fi
log "   ✓ Cleanup complete"

# 3. Verify IBC configuration
log "[3/6] Validating IBC configuration..."
if ! grep -q "IbLoginId=amakua444" ~/IBC/config.ini; then
    die "IBC config: Invalid or missing IbLoginId"
fi
if ! grep -q "AcceptIncomingConnectionAction=accept" ~/IBC/config.ini; then
    log "   WARNING: AcceptIncomingConnectionAction not set to 'accept'"
fi
log "   ✓ IBC config valid"

# 4. Start IB Gateway via IBC
log "[4/6] Starting IB Gateway (IBC automation)..."
cd ~/IBC
nohup ./gatewaystart.sh -inline > "${LOG_DIR}/ibc_output_${TIMESTAMP}.log" 2>&1 &
IBC_PID=$!
log "   IBC PID: ${IBC_PID}"

# 5. Wait for port 4002 (max 120 seconds)
log "[5/6] Waiting for API port 4002..."
WAIT_TIME=0
MAX_WAIT=120
while [ ${WAIT_TIME} -lt ${MAX_WAIT} ]; do
    if nc -z 127.0.0.1 4002 2>/dev/null; then
        log "   ✓ Port 4002 is listening (after ${WAIT_TIME}s)"
        break
    fi
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
done

if [ ${WAIT_TIME} -ge ${MAX_WAIT} ]; then
    die "Port 4002 not ready after ${MAX_WAIT}s"
fi

# 6. API connectivity test
log "[6/6] Testing API connectivity..."
sleep 10  # Additional grace period for API initialization
if timeout 10 /home/davidsanker/venv/bin/python3 -c "
from ib_insync import IB
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=998)
    ib.disconnect()
    exit(0)
except Exception as e:
    print(f'API test failed: {e}')
    exit(1)
" 2>&1 | tee -a "${LOG_FILE}"; then
    log "   ✓ API connectivity confirmed"
else
    log "   WARNING: API test failed, but port is listening. Gateway may need more time to initialize."
fi

log "=========================================="
log "IB Gateway startup complete"
log "Log: ${LOG_FILE}"
log "=========================================="

exit 0
