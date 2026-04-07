#!/bin/bash
###############################################################################
# Production Paper Trading Runner
# Runs automated paper trading during market hours with full safety guardrails
###############################################################################

set -euo pipefail

# Paths
PLATFORM="/home/davidsanker/platform"
SESSION_ID=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$PLATFORM/logs/paper_production"
SESSION_LOG="$LOG_DIR/production_${SESSION_ID}.log"
SUMMARY_DIR="$PLATFORM/logs/daily_summaries"
TODAY_SUMMARY="$SUMMARY_DIR/$(date +%Y-%m-%d).json"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$SUMMARY_DIR"

# Configuration
source "$PLATFORM/config/quantum_runtime.env"

# Safety parameters
CYCLE_INTERVAL_SEC=300  # 5 minutes
MAX_ORDERS_PER_DAY=${PILOT_MAX_ORDERS_PER_DAY:-3}
KILL_SWITCH="$PLATFORM/EMERGENCY_STOP"
PAPER_PROOF="$PLATFORM/state/paper_account_ok.txt"

# Paper Execution Mode (DEFAULT: false = DRY_RUN monitoring only)
# Set to true in quantum_runtime.env to enable paper order execution
PAPER_EXECUTION_MODE=${PAPER_EXECUTION_MODE:-false}

# Metrics
CYCLES_RUN=0
ORDERS_ATTEMPTED=0
ORDERS_EXECUTED=0
CYCLES_BLOCKED=0
START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LAST_ERROR=""

###############################################################################
# LOGGING FUNCTIONS
###############################################################################

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$SESSION_LOG"
}

error() {
    log "ERROR: $*"
    LAST_ERROR="$*"
}

###############################################################################
# SAFETY CHECKS
###############################################################################

check_kill_switch() {
    if [ -f "$KILL_SWITCH" ]; then
        error "KILL SWITCH DETECTED - HALTING ALL TRADING"
        return 1
    fi
    return 0
}

check_gateway() {
    log "Checking IB Gateway..."
    if ! "$PLATFORM/bin/validate_ib_gateway.sh" paper 2>&1 | tee -a "$SESSION_LOG" | grep -q "API handshake successful"; then
        error "IB Gateway validation failed"
        return 1
    fi
    log "✓ IB Gateway operational"
    return 0
}

refresh_paper_proof() {
    # Check if paper proof exists and is recent enough
    if [ ! -f "$PAPER_PROOF" ]; then
        log "Paper proof not found - creating..."
        "$PLATFORM/bin/assert_paper_account.py" >> "$SESSION_LOG" 2>&1 || return 1
        return 0
    fi

    # Check age (need stat -c %s for Linux, stat -f %m for macOS)
    if stat -c %Y "$PAPER_PROOF" >/dev/null 2>&1; then
        # Linux
        PROOF_AGE=$(($(date +%s) - $(stat -c %Y "$PAPER_PROOF")))
    else
        # macOS
        PROOF_AGE=$(($(date +%s) - $(stat -f %m "$PAPER_PROOF")))
    fi

    # Refresh if older than 55 minutes (3300 seconds)
    if [ $PROOF_AGE -gt 3300 ]; then
        log "Paper proof age: ${PROOF_AGE}s - refreshing..."
        "$PLATFORM/bin/assert_paper_account.py" >> "$SESSION_LOG" 2>&1 || return 1
        log "✓ Paper proof refreshed"
    else
        log "✓ Paper proof recent (${PROOF_AGE}s old)"
    fi
    return 0
}

check_config_safety() {
    log "Verifying configuration safety..."

    # Check TRADING_MODE
    if [ "${TRADING_MODE:-}" != "paper" ]; then
        error "TRADING_MODE is not 'paper': ${TRADING_MODE:-unset}"
        return 1
    fi

    # Check ALLOW_LIVE
    if [ "${ALLOW_LIVE:-}" == "true" ]; then
        error "ALLOW_LIVE is TRUE - LIVE TRADING IS FORBIDDEN"
        return 1
    fi

    # Check IB_PORT
    if [ "${IB_PORT:-}" != "4002" ]; then
        error "IB_PORT is not 4002: ${IB_PORT:-unset}"
        return 1
    fi

    log "✓ Configuration safe (paper mode, port 4002, ALLOW_LIVE=false)"
    return 0
}

count_today_orders() {
    # Count execution receipts for today
    TODAY=$(date +%Y-%m-%d)
    if [ -d "$PLATFORM/execution_receipts" ]; then
        find "$PLATFORM/execution_receipts" -name "*${TODAY}*.json" -type f | wc -l
    else
        echo "0"
    fi
}

###############################################################################
# VPA PARSING AND EXECUTION
###############################################################################

get_latest_vpa() {
    # Get the most recent VPA file
    ls -t "$PLATFORM/vpa_storage"/vpa_*.json 2>/dev/null | head -1
}

parse_vpa_decision() {
    # Parse VPA file to extract decision
    # Returns: ACTION|SYMBOL|CONFIDENCE|TARGET_VALUE_PCT
    local vpa_file="$1"

    if [ ! -f "$vpa_file" ]; then
        echo "ERROR|VPA not found"
        return 1
    fi

    # Parse using python3 for JSON extraction
    python3 -c "
import json
import sys
try:
    with open('$vpa_file', 'r') as f:
        vpa = json.load(f)
    plan = vpa.get('decision_plan', {})
    action = plan.get('action', 'HOLD')
    symbol = plan.get('symbol', 'UNKNOWN')
    confidence = plan.get('confidence', 0.0)
    target_pct = plan.get('target_value_pct', 0.0)
    print(f'{action}|{symbol}|{confidence}|{target_pct}')
except Exception as e:
    print(f'ERROR|{str(e)}', file=sys.stderr)
    sys.exit(1)
" 2>> "$SESSION_LOG"
}

check_pilot_guardrails() {
    # Run pilot guardrails check
    # Returns: 0 if pass, 1 if fail
    local symbol="$1"
    local action="$2"
    local target_pct="$3"

    log "Checking pilot guardrails..."

    # Call pilot_guardrails.py
    if python3 "$PLATFORM/bin/pilot_guardrails.py" "$symbol" "$action" "$target_pct" >> "$SESSION_LOG" 2>&1; then
        log "✓ Pilot guardrails passed"
        return 0
    else
        log "✗ Pilot guardrails failed"
        return 1
    fi
}

execute_vpa() {
    # Execute VPA using vpa_executor
    # Creates execution receipt even if blocked
    local vpa_file="$1"

    log "Executing VPA: $vpa_file"

    # Call vpa_executor with --dry-run false (paper execution allowed)
    if python3 "$PLATFORM/bin/vpa_executor.py" \
        --vpa-file "$vpa_file" \
        --config "$PLATFORM/config/quantum_runtime.env" \
        --dry-run false >> "$SESSION_LOG" 2>&1; then
        log "✓ VPA execution completed"
        return 0
    else
        log "✗ VPA execution failed (receipt created)"
        return 1  # Still returns 1 if blocked, but receipt is created
    fi
}

###############################################################################
# MARKET HOURS CHECK
###############################################################################

is_market_hours() {
    # Check if within market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
    # Current time in UTC
    CURRENT_HOUR=$(date -u +%H)
    CURRENT_DAY=$(date -u +%u)  # 1=Monday, 7=Sunday

    # Weekend check
    if [ $CURRENT_DAY -ge 6 ]; then
        log "Weekend - outside market hours"
        return 1
    fi

    # Market hours in UTC (approximate): 14:30 - 21:00 UTC (9:30-4:00 ET)
    # Using 15:00 - 21:00 UTC for Berlin time context
    if [ $CURRENT_HOUR -lt 15 ] || [ $CURRENT_HOUR -ge 21 ]; then
        log "Outside market hours (hour: ${CURRENT_HOUR} UTC)"
        return 1
    fi

    return 0
}

###############################################################################
# TRADING CYCLE
###############################################################################

run_one_cycle() {
    log "=========================================="
    log "Starting trading cycle..."
    log "=========================================="

    # Pre-checks
    check_kill_switch || return 1

    # Check if we've hit daily orders cap
    TODAY_ORDERS=$(count_today_orders)
    log "Orders today: ${TODAY_ORDERS}/${MAX_ORDERS_PER_DAY}"

    if [ $TODAY_ORDERS -ge $MAX_ORDERS_PER_DAY ]; then
        log "Daily orders cap reached - skipping cycle"
        CYCLES_BLOCKED=$((CYCLES_BLOCKED + 1))
        return 0
    fi

    # Refresh paper proof if needed
    refresh_paper_proof || return 1

    # Run trading cycle using single-cycle script
    log "Running trading cycle..."

    # Use single-cycle script (runs one cycle and exits)
    # CRITICAL FIX: was calling run_phase4b_pilot.py (5 cycles, 25+ min), causing systemd timeout
    # CRITICAL FIX 2: python3 from PATH (systemd sets PATH=%h/venv/bin:/usr/bin:/bin)
    if python3 "$PLATFORM/bin/run_one_cycle.py" >> "$SESSION_LOG" 2>&1; then
        CYCLES_RUN=$((CYCLES_RUN + 1))
        log "✓ Cycle completed"

        # NEW: Paper execution logic
        if [ "$PAPER_EXECUTION_MODE" = "true" ]; then
            log "Paper execution mode: ENABLED"

            # Get latest VPA
            LATEST_VPA=$(get_latest_vpa)
            if [ -z "$LATEST_VPA" ]; then
                log "No VPA file found - skipping execution"
                return 0
            fi

            log "Latest VPA: $LATEST_VPA"

            # Parse VPA decision
            DECISION=$(parse_vpa_decision "$LATEST_VPA")
            ACTION=$(echo "$DECISION" | cut -d'|' -f1)
            SYMBOL=$(echo "$DECISION" | cut -d'|' -f2)
            CONFIDENCE=$(echo "$DECISION" | cut -d'|' -f3)
            TARGET_PCT=$(echo "$DECISION" | cut -d'|' -f4)

            log "Decision: $ACTION $SYMBOL (confidence: $CONFIDENCE, target: $TARGET_PCT%)"

            # Execute if BUY/SELL decision
            if [ "$ACTION" = "BUY" ] || [ "$ACTION" = "SELL" ]; then
                log "Tradeable decision detected - checking guardrails..."

                # Check pilot guardrails
                if check_pilot_guardrails "$SYMBOL" "$ACTION" "$TARGET_PCT"; then
                    # Guardrails passed - execute VPA
                    log "Guardrails passed - executing paper order..."
                    ORDERS_ATTEMPTED=$((ORDERS_ATTEMPTED + 1))

                    if execute_vpa "$LATEST_VPA"; then
                        log "✓ Paper order executed successfully"
                    else
                        log "✗ Paper order execution failed (receipt created)"
                    fi
                else
                    log "✗ Guardrails failed - order blocked (receipt will be created)"
                    # TODO: Create block receipt
                fi
            else
                log "HOLD decision - no execution needed"
            fi
        else
            log "Paper execution mode: DISABLED (DRY_RUN monitoring only)"
        fi

        # Check if any orders were placed (by checking for new receipts)
        sleep 2  # Give time for receipts to be written
        NEW_ORDERS=$(count_today_orders)
        if [ $NEW_ORDERS -gt $TODAY_ORDERS ]; then
            ORDERS_EXECUTED=$((ORDERS_EXECUTED + (NEW_ORDERS - TODAY_ORDERS)))
            log "✓ New orders placed: $((NEW_ORDERS - TODAY_ORDERS))"
        fi
    else
        error "Cycle failed - check logs"
        CYCLES_BLOCKED=$((CYCLES_BLOCKED + 1))
        return 1
    fi

    return 0
}

###############################################################################
# SUMMARY GENERATION
###############################################################################

write_summary() {
    END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    cat > "$TODAY_SUMMARY" <<EOF
{
  "date": "$(date +%Y-%m-%d)",
  "session_start": "$START_TIME",
  "session_end": "$END_TIME",
  "cycles_run": $CYCLES_RUN,
  "cycles_blocked": $CYCLES_BLOCKED,
  "orders_attempted": $ORDERS_ATTEMPTED,
  "orders_executed": $ORDERS_EXECUTED,
  "last_error": "$LAST_ERROR",
  "trading_mode": "${TRADING_MODE:-paper}",
  "allow_live": "${ALLOW_LIVE:-false}",
  "ib_port": "${IB_PORT:-4002}"
}
EOF

    log "Summary written to $TODAY_SUMMARY"
}

###############################################################################
# MAIN LOOP
###############################################################################

main() {
    log "=========================================="
    log "PRODUCTION PAPER TRADING STARTED"
    log "=========================================="
    log "Session: ${SESSION_ID}"
    log "Max orders/day: ${MAX_ORDERS_PER_DAY}"
    log "Cycle interval: ${CYCLE_INTERVAL_SEC}s"
    log "=========================================="

    # Initial safety checks
    # Note: These use exit 0 for expected conditions (kill switch, gateway down, market closed)
    # Only exit 1 for unexpected internal errors
    if ! check_kill_switch; then
        log "Expected condition: Kill switch active"
        write_summary
        exit 0
    fi

    if ! check_gateway; then
        log "Expected condition: Gateway not ready"
        write_summary
        exit 0
    fi

    if ! check_config_safety; then
        error "CRITICAL: Configuration safety check failed - THIS IS A BUG"
        write_summary
        exit 1  # Real error - bad configuration
    fi

    if ! refresh_paper_proof; then
        log "Expected condition: Paper proof not available"
        write_summary
        exit 0
    fi

    # Check if market hours
    if ! is_market_hours; then
        log "Outside market hours - exiting"
        write_summary
        exit 0
    fi

    log "Market hours confirmed - starting trading loop"

    # Main trading loop
    while true; do
        # Check kill switch
        if ! check_kill_switch; then
            log "Kill switch activated - stopping gracefully"
            write_summary
            exit 0
        fi

        # Check market hours (stop if market closes)
        if ! is_market_hours; then
            log "Market hours ended - stopping"
            break
        fi

        # Run one trading cycle
        if run_one_cycle; then
            log "Cycle successful"
        else
            log "Cycle failed - will retry after interval"
        fi

        # Check if we should continue
        if [ $CYCLES_RUN -ge 100 ]; then
            log "Max cycles reached - stopping"
            break
        fi

        # Wait for next cycle
        log "Waiting ${CYCLE_INTERVAL_SEC}s for next cycle..."
        sleep $CYCLE_INTERVAL_SEC
    done

    # Write final summary
    write_summary

    log "=========================================="
    log "PRODUCTION PAPER TRADING ENDED"
    log "=========================================="
    log "Cycles run: ${CYCLES_RUN}"
    log "Cycles blocked: ${CYCLES_BLOCKED}"
    log "Orders executed: ${ORDERS_EXECUTED}"
    log "=========================================="
}

# Run main function
main "$@"
