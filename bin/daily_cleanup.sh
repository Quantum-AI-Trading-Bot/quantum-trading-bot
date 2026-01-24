#!/bin/bash
# Daily system cleanup

LOG_FILE="/home/davidsanker/platform/logs/maintenance/daily_$(date +%Y%m%d).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] Starting daily cleanup..." >> "$LOG_FILE"

# Clean old logs (keep 7 days)
find /home/davidsanker/platform/logs -name "*.log" -mtime +7 -delete 2>/dev/null

# Clean temporary files
find /tmp -name "*trading*" -type f -mtime +1 -delete 2>/dev/null
find /tmp -name "*gateway*" -type f -mtime +1 -delete 2>/dev/null

# Compress old logs (keep 30 days compressed)
find /home/davidsanker/platform/logs -name "*.log" -mtime +7 -exec gzip {} \; 2>/dev/null

echo "[$(date)] Daily cleanup completed" >> "$LOG_FILE"
