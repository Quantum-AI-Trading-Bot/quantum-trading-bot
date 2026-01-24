#!/bin/bash
# Learning Pipeline - Ingest receipts and update learner
# Usage: learning_pipeline.sh [--recent-only]

set -e

PLATFORM_ROOT="/home/davidsanker/platform"
LOG_DIR="$PLATFORM_ROOT/logs/quantum-engine"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] 🔄 Learning Pipeline Started"

# Step 1: Ingest execution receipts
echo "[$TIMESTAMP] Step 1: Ingesting execution receipts..."
python3 "$PLATFORM_ROOT/bin/ingest_executions.py" --quiet --recent-only

# Step 2: Update learner
echo "[$TIMESTAMP] Step 2: Updating learner..."
python3 "$PLATFORM_ROOT/bin/run_learning_update.py" --quiet

echo "[$TIMESTAMP] ✅ Learning Pipeline Complete"
