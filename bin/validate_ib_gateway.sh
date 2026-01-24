#!/bin/bash
# validate_ib_gateway.sh - Validate IB Gateway API is ready
# Exit codes:
#   0 = All OK (gateway running + ib_insync handshake successful)
#   2 = Gateway process not running
#   3 = (deprecated - port check removed, using handshake instead)
#   4 = Handshake/auth required (API not ready or connection refused)
#   5 = Dependencies missing (python3/ib_insync not available)

set -e

# Configuration
GATEWAY_PROCESS="ibgateway|GWClient|install4j|tws"
API_PORT=4002
API_HOST="127.0.0.1"
TIMEOUT=5
VENV_PYTHON="/home/davidsanker/venv/bin/python"

# Determine which Python to use (prefer venv if available)
if [ -x "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
else
    PYTHON_CMD="python3"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check 1: Gateway process running
log "Checking IB Gateway process..."
if ! pgrep -f "$GATEWAY_PROCESS" > /dev/null 2>&1; then
    log "${RED}✗ Gateway process not found${NC}"
    exit 2
fi
log "${GREEN}✓ Gateway process running${NC}"

# Check 2: ib_insync handshake (required - tests actual IB API protocol)
log "Attempting IB API handshake..."
if [ -x "$PYTHON_CMD" ]; then
    # Try to import ib_insync and connect
    HANDSHAKE_TEST=$(cat << 'PYTHON'
import sys
try:
    from ib_insync import IB
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=3)
    ib.disconnect()
    print("OK")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
PYTHON
)

    HANDSHAKE_RESULT=$(timeout $TIMEOUT $PYTHON_CMD -c "$HANDSHAKE_TEST" 2>&1 || echo "TIMEOUT")
    
    if echo "$HANDSHAKE_RESULT" | grep -q "OK"; then
        log "${GREEN}✓ API handshake successful${NC}"
        exit 0
    elif echo "$HANDSHAKE_RESULT" | grep -q "ERROR.*Connect.*refused\|ERROR.*Connection.*reset"; then
        log "${YELLOW}⚠ Port listening but API not ready (authentication required)${NC}"
        exit 4
    else
        log "${YELLOW}⚠ Handshake failed (may need authentication): $HANDSHAKE_RESULT${NC}"
        exit 4
    fi
else
    log "${RED}✗ Python not available: $PYTHON_CMD (required for validation)${NC}"
    exit 5  # Dependencies missing
fi

exit 5  # Should not reach here
