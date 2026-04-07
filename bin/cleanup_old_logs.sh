#!/bin/bash
# Cleanup old session log directories
# Keeps only the last 14 days of session logs

LOG_DIR="/home/davidsanker/logs"
RETENTION_DAYS=14

echo "========================================="
echo "Log Cleanup: $(date)"
echo "========================================="

# Find and remove old session directories
REMOVED=$(find "$LOG_DIR" -maxdepth 1 -type d -name "*202601*" -mtime +$RETENTION_DAYS 2>/dev/null | wc -l)

if [ $REMOVED -gt 0 ]; then
    echo "Removing $REMOVED old session directories (older than $RETENTION_DAYS days)..."
    find "$LOG_DIR" -maxdepth 1 -type d -name "*202601*" -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null
    echo "✅ Removed $REMOVED old session directories"
else
    echo "✅ No old session directories to remove"
fi

# Show current logs directory size
SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | awk '{print $1}')
echo "Current logs directory size: $SIZE"

echo "========================================="
echo "Cleanup Complete"
echo "========================================="
