#!/bin/bash
#
# IB Gateway Installation Integrity Check
# Verifies installation health and detects corruption
#
# Exit codes:
#   0 - OK
#   10 - Missing installer artifact
#   11 - Install missing files
#   12 - Corruption markers in logs
#   13 - Java missing/incompatible
#

set -e

GATEWAY_DIR="/home/davidsanker/IBGateway"
IBC_DIR="/home/davidsanker/IBC"
INSTALLER_DIR="/home/davidsanker/archives/installers"
ARCHIVE_DIR="/home/davidsanker/archives/ibgateway_backup"
LOG_DIR="/home/davidsanker/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS_FOUND=0

echo "=========================================="
echo "🔍 IB Gateway Installation Check"
echo "=========================================="
echo ""

# Check 1: Java installation
echo "[1/6] Checking Java installation..."
if command -v java >/dev/null 2>&1; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    echo -e "${GREEN}✅${NC} Java installed: $JAVA_VERSION"
else
    echo -e "${RED}❌${NC} Java NOT found"
    ERRORs_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# Check 2: IB Gateway directory exists
echo "[2/6] Checking IB Gateway directory..."
if [ -d "$GATEWAY_DIR" ]; then
    echo -e "${GREEN}✅${NC} IB Gateway directory exists: $GATEWAY_DIR"
else
    echo -e "${RED}❌${NC} IB Gateway directory NOT found: $GATEWAY_DIR"
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# Check 3: Critical files and directories
echo "[3/6] Checking critical files..."
REQUIRED_FILES=(
    "$GATEWAY_DIR/ibgateway.bin"
    "$GATEWAY_DIR/jars"
    "$GATEWAY_DIR/.install4j/i4jruntime.jar"
    "$GATEWAY_DIR/.install4j/launcher*.jar"
)

MISSING_FILES=0
for pattern in "${REQUIRED_FILES[@]}"; do
    if ls $pattern 1>/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} Found: $pattern"
    else
        echo -e "  ${RED}❌${NC} Missing: $pattern"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# Check 4: JAR file integrity
echo "[4/6] Checking JAR file integrity..."
if [ -d "$GATEWAY_DIR/jars" ]; then
    JAR_COUNT=$(find "$GATEWAY_DIR/jars" -name "*.jar" -type f | wc -l)
    echo -e "  ${GREEN}✅${NC} Found $JAR_COUNT JAR files in jars/"

    if [ $JAR_COUNT -lt 20 ]; then
        echo -e "  ${YELLOW}⚠️${NC}  WARNING: Low JAR count (expected 20+)"
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
    fi
else
    echo -e "  ${RED}❌${NC} jars/ directory missing"
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# Check 5: Corruption markers in logs
echo "[5/6] Checking for corruption markers in logs..."

LOG_FILES=(
    "$IBC_DIR/Logs/ibc-*.txt"
    "$GATEWAY_DIR/launcher.log"
    "$LOG_DIR/ib_reinstall/gateway_start_trace.log"
)

CORRUPTION_MARKERS=(
    "NoClassDefFoundError.*install4j"
    "ClassNotFoundException.*install4j"
    "Exiting with exit code=1107"
)

MARKER_FOUND=0
for log_pattern in "${LOG_FILES[@]}"; do
    for log_file in $log_pattern; do
        if [ -f "$log_file" ]; then
            for marker in "${CORRUPTION_MARKERS[@]}"; do
                if grep -qiE "$marker" "$log_file" 2>/dev/null; then
                    echo -e "  ${RED}❌${NC} Corruption marker found in: $log_file"
                    echo -e "     Marker: $marker"
                    MARKER_FOUND=1
                fi
            done
        fi
    done
done

if [ $MARKER_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✅${NC} No corruption markers in logs"
else
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# Check 6: IBC configuration
echo "[6/6] Checking IBC configuration..."
if [ -f "$IBC_DIR/config.ini" ]; then
    echo -e "  ${GREEN}✅${NC} IBC config exists: $IBC_DIR/config.ini"

    # Check for critical settings (non-secret)
    if grep -q "TradingMode=paper" "$IBC_DIR/config.ini"; then
        echo -e "  ${GREEN}✅${NC} TradingMode configured"
    else
        echo -e "  ${YELLOW}⚠️${NC}  TradingMode not set to paper"
    fi

    if grep -q "ApiPort=4002" "$IBC_DIR/config.ini"; then
        echo -e "  ${GREEN}✅${NC} ApiPort configured (4002)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  ApiPort not 4002"
    fi

    if grep -q "EnableApi=yes" "$IBC_DIR/config.ini"; then
        echo -e "  ${GREEN}✅${NC} API enabled"
    else
        echo -e "  ${YELLOW}⚠️${NC}  API may not be enabled"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  IBC config not found (will need to configure)"
fi
echo ""

# Final verdict
echo "=========================================="
if [ $ERRORS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ INSTALLATION HEALTHY${NC}"
    echo "=========================================="
    exit 0
elif [ $MARKER_FOUND -eq 1 ]; then
    echo -e "${RED}❌ CORRUPTION DETECTED${NC}"
    echo "=========================================="
    echo ""
    echo "Corruption markers found in logs indicate"
    echo "install4j dependency issues."
    echo ""
    echo "Action required:"
    echo "  /home/davidsanker/platform/bin/reinstall_ib_gateway.sh"
    exit 12
elif [ $MISSING_FILES -gt 0 ]; then
    echo -e "${RED}❌ INSTALLATION INCOMPLETE${NC}"
    echo "=========================================="
    exit 11
else
    echo -e "${YELLOW}⚠️  INSTALLATION HAS WARNINGS${NC}"
    echo "=========================================="
    exit 0
fi
