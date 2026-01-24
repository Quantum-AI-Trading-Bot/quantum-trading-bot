#!/bin/bash
# Trading Email Report Sender - Enhanced with subject suffix support
# Updated: 2026-01-22
# Purpose: Send trading system report 3x daily with OPEN/MID/CLOSE suffixes

set -euo pipefail

PLATFORM_ROOT="/home/davidsanker/platform"
CONFIG_FILE="$PLATFORM_ROOT/config/email_report.env"
REPORT_SCRIPT="$PLATFORM_ROOT/bin/generate_trading_email_report.py"
SMTP_SCRIPT="$PLATFORM_ROOT/bin/send_email_smtp.py"

# Default values
EMAIL_FROM="${EMAIL_FROM:-david@sanker.at}"
EMAIL_TO="${EMAIL_TO:-david@sanker.at}"
SUBJECT_PREFIX="${SUBJECT_PREFIX:-[TradingBot]}"
TIMEZONE="${TIMEZONE:-Europe/Berlin}"
DRY_RUN=0
SUBJECT_SUFFIX=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --subject-suffix)
            SUBJECT_SUFFIX="$2"
            shift 2
            ;;
        --to)
            EMAIL_TO="$2"
            shift 2
            ;;
        --from)
            EMAIL_FROM="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--subject-suffix OPEN|MID|CLOSE] [--to email] [--from email] [--config path]"
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
        value=$(echo "$value" | xargs | sed 's/^["'"'"']//;s/["'"'"']$//')
        export "$key=$value"
    done < "$CONFIG_FILE"
fi

# Override with config values if set
if [ -n "${EMAIL_TO:-}" ]; then
    EMAIL_TO="$EMAIL_TO"
fi

if [ -n "${EMAIL_FROM:-}" ]; then
    EMAIL_FROM="$EMAIL_FROM"
fi

if [ -n "${SUBJECT_PREFIX:-}" ]; then
    SUBJECT_PREFIX="$SUBJECT_PREFIX"
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

# Build subject with timezone-aware timestamp
if [ -n "$SUBJECT_SUFFIX" ]; then
    SUBJECT="$SUBJECT_PREFIX $SUBJECT_SUFFIX - $(TZ='Europe/Berlin' date +'%Y-%m-%d %H:%M Berlin')"
else
    SUBJECT="$SUBJECT_PREFIX Trading System Report - $(TZ='Europe/Berlin' date +'%Y-%m-%d %H:%M Berlin')"
fi

# Dry-run mode: just print report
if [ $DRY_RUN -eq 1 ]; then
    echo ""
    echo "========================================"
    echo "DRY-RUN MODE: Report would be sent to:"
    echo "  From: $EMAIL_FROM"
    echo "  To: $EMAIL_TO"
    echo "  Subject: $SUBJECT"
    echo "========================================"
    echo ""
    echo "$REPORT_DATA"
    echo ""
    echo "========================================"
    echo "To send actual email, run without --dry-run"
    echo "========================================"
    exit 0
fi

# Try sending via Python SMTP (preferred)
echo "Attempting to send email via SMTP..."
if python3 "$SMTP_SCRIPT" --to "$EMAIL_TO" --subject "$SUBJECT" --file "$REPORT_FILE" 2>&1; then
    echo "✓ Report sent to $EMAIL_TO via SMTP"
    exit 0
fi

# Fallback: Try mail command
echo "⚠ SMTP failed, trying mail command..."
if command -v mail >/dev/null 2>&1; then
    if mail -s "$SUBJECT" -r "$EMAIL_FROM" "$EMAIL_TO" < "$REPORT_FILE" 2>&1; then
        echo "✓ Report sent to $EMAIL_TO via mail command"
        exit 0
    else
        echo "⚠ mail command failed"
    fi
fi

# Fallback: Try sendmail
echo "⚠ mail failed, trying sendmail..."
if command -v sendmail >/dev/null 2>&1; then
    if {
        echo "Subject: $SUBJECT"
        echo "From: $EMAIL_FROM"
        echo "To: $EMAIL_TO"
        echo ""
        cat "$REPORT_FILE"
    } | sendmail -t -i 2>&1; then
        echo "✓ Report sent to $EMAIL_TO via sendmail"
        exit 0
    else
        echo "⚠ sendmail failed"
    fi
fi

# All transports failed - save to log
echo "❌ All email transports failed, saving to log file..."
LOG_FILE="$PLATFORM_ROOT/logs/email_report_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p "$PLATFORM_ROOT/logs"
{
    echo "Email delivery failed - report saved to log"
    echo "To: $EMAIL_TO"
    echo "From: $EMAIL_FROM"
    echo "Subject: $SUBJECT"
    echo "Date: $(date -R)"
    echo ""
    echo "$REPORT_DATA"
} > "$LOG_FILE"
echo "→ Report saved to: $LOG_FILE"
echo ""
echo "To enable email delivery, check:"
echo "  1. SMTP credentials in: $SMTP_SCRIPT"
echo "  2. Or configure system MTA (postfix/sendmail)"
echo "  3. Or install msmtp: sudo apt-get install msmtp msmtp-mta"
exit 0
