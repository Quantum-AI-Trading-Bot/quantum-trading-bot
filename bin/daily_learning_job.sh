#!/bin/bash
###############################################################################
# Daily Learning Job
# Ingests executions and updates learner state
###############################################################################

set -euo pipefail

# Paths
PLATFORM="/home/davidsanker/platform"
LOG_DIR="$PLATFORM/logs/daily_learning"
SESSION_ID=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/learning_${SESSION_ID}.log"
SUMMARY_DIR="$PLATFORM/logs/daily_summaries"
TODAY_SUMMARY="$SUMMARY_DIR/$(date +%Y-%m-%d).json"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$SUMMARY_DIR"

# Logging
log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*"
}

###############################################################################
# MAIN
###############################################################################

main() {
    log "=========================================="
    log "DAILY LEARNING JOB STARTED"
    log "=========================================="

    # Get baseline counts
    BEFORE_TRADES=0
    BEFORE_OUTCOMES=0
    if [ -f "$PLATFORM/state/ledgers/trades.jsonl" ]; then
        BEFORE_TRADES=$(wc -l < "$PLATFORM/state/ledgers/trades.jsonl")
    fi
    if [ -f "$PLATFORM/state/ledgers/outcomes.jsonl" ]; then
        BEFORE_OUTCOMES=$(wc -l < "$PLATFORM/state/ledgers/outcomes.jsonl")
    fi

    log "Before: trades=${BEFORE_TRADES}, outcomes=${BEFORE_OUTCOMES}"

    # Ingest executions
    log "Step 1: Ingesting execution receipts..."
    if "/home/davidsanker/venv/bin/python" "$PLATFORM/bin/ingest_executions.py" >> "$LOG_FILE" 2>&1; then
        log "✓ Ingest completed"
    else
        error "Ingest failed - check logs"
        return 1
    fi

    # Update learner
    log "Step 2: Updating learner..."
    if "/home/davidsanker/venv/bin/python" "$PLATFORM/bin/run_learning_update.py" >> "$LOG_FILE" 2>&1; then
        log "✓ Learner updated"
    else
        error "Learner update failed - check logs"
        # Don't return error, learner update may fail if no new data
    fi

    # Get after counts
    AFTER_TRADES=0
    AFTER_OUTCOMES=0
    if [ -f "$PLATFORM/state/ledgers/trades.jsonl" ]; then
        AFTER_TRADES=$(wc -l < "$PLATFORM/state/ledgers/trades.jsonl")
    fi
    if [ -f "$PLATFORM/state/ledgers/outcomes.jsonl" ]; then
        AFTER_OUTCOMES=$(wc -l < "$PLATFORM/state/ledgers/outcomes.jsonl")
    fi

    log "After: trades=${AFTER_TRADES}, outcomes=${AFTER_OUTCOMES}"

    # Update daily summary with learning info
    if [ -f "$TODAY_SUMMARY" ]; then
        # Append learning info to existing summary
        TEMP_SUMMARY=$(mktemp)
        jq --arg trades_delta $((AFTER_TRADES - BEFORE_TRADES)) \
           --arg outcomes_delta $((AFTER_OUTCOMES - BEFORE_OUTCOMES)) \
           --arg learner_updated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
           '. + {"learning": {"trades_delta": ($trades_delta|tonumber), "outcomes_delta": ($outcomes_delta|tonumber), "learner_updated": $learner_updated}}' \
           "$TODAY_SUMMARY" > "$TEMP_SUMMARY"
        mv "$TEMP_SUMMARY" "$TODAY_SUMMARY"
        log "✓ Daily summary updated"
    fi

    log "=========================================="
    log "DAILY LEARNING JOB COMPLETE"
    log "=========================================="
}

main "$@"
