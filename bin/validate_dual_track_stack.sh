#!/bin/bash
# validate_dual_track_stack.sh - Validate entire dual-track stack health

set -e

PLATFORM_ROOT="/home/davidsanker/platform"
EXIT_CODE=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Dual-Track Stack Validation ==="
echo ""

# Check 1: Emergency stop
if [ -f "$PLATFORM_ROOT/EMERGENCY_STOP" ]; then
    echo "${RED}✗ EMERGENCY_STOP file exists${NC}"
    EXIT_CODE=3
else
    echo "${GREEN}✓ No emergency stop${NC}"
fi

# Check 2: IB Gateway
echo ""
echo "IB Gateway Status:"
if "$PLATFORM_ROOT/bin/validate_ib_gateway.sh" > /dev/null 2>&1; then
    echo "${GREEN}✓ IB Gateway healthy${NC}"
    
    # Also check port
    if ss -ltnp | grep -q :4002; then
        echo "${GREEN}✓ Port 4002 listening${NC}"
    fi
else
    VALID_EXIT=$?
    echo "${RED}✗ IB Gateway unhealthy (exit code $VALID_EXIT)${NC}"
    EXIT_CODE=1
fi

# Check 3: Watchdog
echo ""
echo "Watchdog Status:"
if systemctl --user is-active --quiet ibgateway-watchdog.service; then
    echo "${GREEN}✓ Watchdog running${NC}"
else
    echo "${YELLOW}⚠ Watchdog not running${NC}"
fi

# Check 4: VPA Storage (Track B)
echo ""
echo "VPA Storage:"
if [ -d "$PLATFORM_ROOT/vpa_storage" ]; then
    VPA_COUNT=$(find "$PLATFORM_ROOT/vpa_storage" -name "vpa_*.json" | wc -l)
    echo "${GREEN}✓ VPA storage exists ($VPA_COUNT artifacts)${NC}"
else
    echo "${YELLOW}⚠ VPA storage not found${NC}"
fi

# Check 5: Logs
echo ""
echo "Log Directories:"
for dir in ib-gateway trading-bot quantum-engine; do
    if [ -d "$PLATFORM_ROOT/logs/$dir" ]; then
        echo "${GREEN}✓ logs/$dir exists${NC}"
    else
        echo "${YELLOW}⚠ logs/$dir missing${NC}"
    fi
done

# Summary
echo ""
echo "=== Summary ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo "${GREEN}✓ All checks passed${NC}"
else
    echo "${RED}✗ Stack unhealthy (exit code $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
