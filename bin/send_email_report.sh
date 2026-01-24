#!/bin/bash
# Email Report Sender - Safe wrapper for email delivery with SMTP fallback
# Updated: 2026-01-22 07:49:00 UTC
# Purpose: Send trading system report via email with dry-run support

set -euo pipefail

PLATFORM_ROOT="/home/davidsanker/platform"
CONFIG_FILE="$PLATFORM_ROOT/config/email_report.env"
REPORT_SCRIPT="$PLATFORM_ROOT/bin/generate_email_report.py"
SMTP_SCRIPT="$PLATFORM_ROOT/bin/send_email_smtp.py"

# Default values
ALERT_EMAIL="${ALERT_EMAIL:-david@sanker.at}"
SUBJECT_PREFIX="${SUBJECT_PREFIX:-[TradingBot]}"
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --to)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--to email] [--config path]"
            exit 1
            ;;
    esac
done

# Load config if exists
if [ -f "$CONFIG_FILE" ]; then
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        export "$key=$value"
    done < "$CONFIG_FILE"
fi

# Override with config values if set
if [ -n "${ALERT_EMAIL_CONFIG:-}" ]; then
    ALERT_EMAIL="$ALERT_EMAIL_CONFIG"
fi

if [ -n "${SUBJECT_PREFIX_CONFIG:-}" ]; then
    SUBJECT_PREFIX="$SUBJECT_PREFIX_CONFIG"
fi

# Generate report
echo "Generating trading system report..."
REPORT_DATA=$(python3 "$REPORT_SCRIPT" 2>&1)
REPORT_EXIT=$?

if [ $REPORT_EXIT -ne 0 ]; then
    echo "Error generating report:" >&2
    echo "$REPORT_DATA" >&2
    exit 1
fi

# Create temp file for report
REPORT_FILE=$(mktemp)
trap "rm -f $REPORT_FILE" EXIT

echo "$REPORT_DATA" > "$REPORT_FILE"

# Dry-run mode: just print report
if [ $DRY_RUN -eq 1 ]; then
    echo ""
    echo "========================================"
    echo "DRY-RUN MODE: Report would be sent to:"
    echo "  To: $ALERT_EMAIL"
    echo "  Subject: $SUBJECT_PREFIX Trading System Report $(date +%Y-%m-%d)"
    echo "========================================"
    echo ""
    echo "$REPORT_DATA"
    echo ""
    echo "========================================"
    echo "To send actual email, run without --dry-run"
    echo "========================================"
    exit 0
fi

# Try sending via Python SMTP (Strato)
SUBJECT="$SUBJECT_PREFIX Trading System Report $(date +%Y-%m-%d)"

echo "Attempting to send email via SMTP..."
if python3 "$SMTP_SCRIPT" --to "$ALERT_EMAIL" --subject "$SUBJECT" --file "$REPORT_FILE" 2>&1; then
    echo "✓ Report sent to $ALERT_EMAIL via SMTP"
    exit 0
else
    echo "⚠ SMTP failed, saving to log file..."
    LOG_FILE="$PLATFORM_ROOT/logs/email_report_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p "$PLATFORM_ROOT/logs"
    {
        echo "Email delivery failed - report saved to log"
        echo "To: $ALERT_EMAIL"
        echo "Subject: $SUBJECT"
        echo "Date: $(date -R)"
        echo ""
        echo "$REPORT_DATA"
    } > "$LOG_FILE"
    echo "→ Report saved to: $LOG_FILE"
    echo ""
    echo "To enable email delivery, check SMTP credentials in:"
    echo "  $SMTP_SCRIPT"
    exit 0
fi
