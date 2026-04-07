#!/bin/bash
# Clear EMERGENCY_STOP Kill Switch
# WARNING: Only run this after verifying:
# 1. IB Gateway is running and listening on port 4002
# 2. Paper account proof has passed
# 3. System is safe for trading

set -e

PLATFORM_ROOT="/home/davidsanker/platform"
EMERGENCY_FILE="$PLATFORM_ROOT/EMERGENCY_STOP"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        EMERGENCY STOP CLEARANCE TOOL                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if EMERGENCY_STOP exists
if [ ! -f "$EMERGENCY_FILE" ]; then
    echo "✓ EMERGENCY_STOP file does not exist - no action needed"
    exit 0
fi

# Show file info
echo "EMERGENCY_STOP file found:"
ls -la "$EMERGENCY_FILE"
echo ""

# Pre-flight checks
echo "Running pre-flight checks..."
echo ""

# Check 1: Port 4002 (PRIMARY CHECK - more reliable than process name)
echo "1. Checking IB Gateway port 4002..."
if ss -ltnp | grep -q ":4002"; then
    echo "   ✓ Port 4002 is listening"
else
    echo "   ✗ Port 4002 is NOT listening"
    echo "   DO NOT CLEAR EMERGENCY_STOP - API port not available"
    exit 1
fi

# Check 2: Run live paper proof
echo "2. Running live paper account proof..."
if source ~/venv/bin/activate && python3 "$PLATFORM_ROOT/bin/assert_paper_account.py" > /tmp/paper_proof_$$.log 2>&1; then
    echo "   ✓ Paper account proof PASSED"
    rm -f /tmp/paper_proof_$$.log
else
    echo "   ✗ Paper account proof FAILED"
    echo "   DO NOT CLEAR EMERGENCY_STOP - Cannot verify paper trading mode"
    echo "   Proof log saved to: /tmp/paper_proof_$$.log"
    echo ""
    echo "   To debug: cat /tmp/paper_proof_$$.log"
    exit 1
fi

# Check 3: Paper proof file (for freshness info)
echo "3. Checking paper proof freshness..."
PAPER_PROOF="$PLATFORM_ROOT/state/paper_account_ok.txt"
if [ -f "$PAPER_PROOF" ]; then
    PROOF_AGE=$(($(date +%s) - $(stat -c %Y "$PAPER_PROOF")))
    if [ $PROOF_AGE -lt 86400 ]; then  # 24 hours
        echo "   ✓ Paper proof is fresh ($(date -d @$(( $(stat -c %Y "$PAPER_PROOF") )) +%Y-%m-%d\ %H:%M:%S))"
    else
        echo "   ⚠ Paper proof is stale ($(date -d @$(( $(stat -c %Y "$PAPER_PROOF") )) +%Y-%m-%d\ %H:%M:%S))"
    fi
else
    echo "   ⚠ Paper proof file not found (but live proof passed above)"
fi

echo ""
echo "All critical checks passed."
echo ""

# Confirm
read -p "Clear EMERGENCY_STOP and resume trading? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled - EMERGENCY_STOP remains active"
    exit 0
fi

# Backup the file
BACKUP_DIR="$PLATFORM_ROOT/logs/incidents"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cleared_stop_${TIMESTAMP}"

mv "$EMERGENCY_FILE" "$BACKUP_FILE"
echo ""
echo "✓ EMERGENCY_STOP cleared and backed up to:"
echo "  $BACKUP_FILE"
echo ""

# Verify trading can resume
echo "Verifying production cycle can run..."
if timeout 10 "$PLATFORM_ROOT/bin/run_paper_production.sh" --dry-run 2>&1 | grep -q "KILL SWITCH"; then
    echo "⚠ Warning: Production script still detects KILL SWITCH"
    echo "   May need to wait for next timer cycle (max 5 minutes)"
else
    echo "✓ Production cycle ready to resume"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  EMERGENCY_STOP CLEARED - Trading should resume shortly       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
