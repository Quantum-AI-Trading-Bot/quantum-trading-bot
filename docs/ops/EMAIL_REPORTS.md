# Trading Bot Email Reports - Operations Guide

**Last Updated**: 2026-01-22
**Status**: ✅ Active (3x daily emails on weekdays)

---

## Overview

The trading bot sends automated email reports 3 times per weekday (Monday-Friday) to provide visibility into system health, trading activity, and learning progress.

**Schedule (Europe/Berlin time)**:
- **OPEN**: 15:35 (US market open ~9:35 AM ET)
- **MID**: 18:30 (US midday ~12:30 PM ET)
- **CLOSE**: 21:55 (US market close ~3:55 PM ET)

---

## Configuration

### Email Settings

Edit `/home/davidsanker/platform/config/email_report.env`:

```bash
# Email addresses
EMAIL_FROM="david@sanker.at"
EMAIL_TO="david@sanker.at"

# Subject prefix
SUBJECT_PREFIX="[TradingBot]"

# Timezone for timestamps
TIMEZONE="Europe/Berlin"

# Report sections (all enabled by default)
INCLUDE_PORTFOLIO=true
INCLUDE_RECEIPTS=true
INCLUDE_VPA=true
INCLUDE_SERVICES=true
INCLUDE_LEARNING=true
```

### Changing Email Recipients

To receive emails at a different address:

```bash
# Method 1: Edit config file
nano /home/davidsanker/platform/config/email_report.env
# Change EMAIL_TO="your-email@example.com"

# Method 2: Override via environment
export EMAIL_TO="your-email@example.com"
systemctl --user restart trading-email-open.service
```

---

## SMTP Configuration

### Current Setup

The system uses multiple email transport methods in order of preference:

1. **Python SMTP** (`send_email_smtp.py`) - Preferred, requires credentials
2. **mail command** (mailutils) - Fallback if configured
3. **sendmail** - Fallback if system MTA installed

### Configuring SMTP (Recommended)

Edit `/home/davidsanker/platform/bin/send_email_smtp.py` and update:

```python
SMTP_HOST = "smtp.sanker.at"  # Your SMTP server
SMTP_PORT = 587
SMTP_USER = "david@sanker.at"
SMTP_FROM = "david@sanker.at"

# For password, create secure file:
# ~/.config/trading_mail/smtp_password (chmod 600)
```

**Create password file** (NEVER commit to git):

```bash
mkdir -p ~/.config/trading_mail
chmod 700 ~/.config/trading_mail
echo "YOUR_SMTP_PASSWORD" > ~/.config/trading_mail/smtp_password
chmod 600 ~/.config/trading_mail/smtp_password
```

### Alternative: Install msmtp

If no SMTP is configured, install msmtp:

```bash
sudo apt-get update
sudo apt-get install -y msmtp msmtp-mta

# Create config: ~/.msmtprc
cat > ~/.msmtprc << 'EOF'
account default
host smtp.sanker.at
port 587
auth on
from david@sanker.at
user david@sanker.at
passwordeval "cat ~/.config/trading_mail/smtp_password"
tls on
EOF

chmod 600 ~/.msmtprc
```

---

## Testing

### Test Report Generation (Dry-Run)

```bash
# Test with OPEN suffix
/home/davidsanker/platform/bin/send_trading_email_report.sh \
  --dry-run \
  --subject-suffix OPEN

# Test with MID suffix
/home/davidsanker/platform/bin/send_trading_email_report.sh \
  --dry-run \
  --subject-suffix MID

# Test with CLOSE suffix
/home/davidsanker/platform/bin/send_trading_email_report.sh \
  --dry-run \
  --subject-suffix CLOSE
```

### Test Email Sending (Actual Send)

```bash
# This will attempt to send a real email
/home/davidsanker/platform/bin/send_trading_email_report.sh \
  --subject-suffix TEST
```

### Test Systemd Services

```bash
# Manually trigger each service
systemctl --user start trading-email-open.service
systemctl --user start trading-email-mid.service
systemctl --user start trading-email-close.service

# Check logs
journalctl --user -u trading-email-open.service -n 50
journalctl --user -u trading-email-mid.service -n 50
journalctl --user -u trading-email-close.service -n 50
```

---

## Monitoring

### Check Timer Status

```bash
# List all trading email timers
systemctl --user list-timers --all | grep trading-email

# Check individual timer status
systemctl --user status trading-email-open.timer
systemctl --user status trading-email-mid.timer
systemctl --user status trading-email-close.timer
```

### View Next Run Times

```bash
# Show all timers with next execution
systemctl --user list-timers | grep email
```

### View Service Logs

```bash
# Recent logs from all email services
journalctl --user -u "trading-email*.service" --since "today"

# Follow logs in real-time
journalctl --user -u "trading-email*.service" -f
```

---

## Schedule Management

### Disable All Emails

```bash
# Stop and disable all timers
systemctl --user disable --now trading-email-open.timer
systemctl --user disable --now trading-email-mid.timer
systemctl --user disable --now trading-email-close.timer
```

### Enable All Emails

```bash
# Enable and start all timers
systemctl --user enable --now trading-email-open.timer
systemctl --user enable --now trading-email-mid.timer
systemctl --user enable --now trading-email-close.timer
```

### Modify Schedule

To change the times, edit the timer files:

```bash
# Edit OPEN timer (currently 15:35 Berlin)
nano ~/.config/systemd/user/trading-email-open.timer
# Change: OnCalendar=Mon..Fri HH:MM:00

# Edit MID timer (currently 18:30 Berlin)
nano ~/.config/systemd/user/trading-email-mid.timer

# Edit CLOSE timer (currently 21:55 Berlin)
nano ~/.config/systemd/user/trading-email-close.timer

# Reload systemd after changes
systemctl --user daemon-reload
systemctl --user restart trading-email-open.timer
systemctl --user restart trading-email-mid.timer
systemctl --user restart trading-email-close.timer
```

---

## Troubleshooting

### Emails Not Arriving

1. **Check service status**:
   ```bash
   systemctl --user status trading-email-open.service
   journalctl --user -u trading-email-open.service -n 50
   ```

2. **Test SMTP manually**:
   ```bash
   python3 /home/davidsanker/platform/bin/send_email_smtp.py --test
   ```

3. **Check fallback log**:
   ```bash
   ls -lt /home/davidsanker/platform/logs/email_report_*
   cat /home/davidsanker/platform/logs/email_report_YYYYMMDD_HHMMSS.txt
   ```

4. **Verify SMTP credentials**:
   ```bash
   cat ~/.config/trading_mail/smtp_password
   # Should exist and contain correct password
   ```

### Report Generation Errors

1. **Test report generator**:
   ```bash
   python3 /home/davidsanker/platform/bin/generate_trading_email_report.py
   ```

2. **Check IB Gateway**:
   ```bash
   /home/davidsanker/platform/bin/validate_ib_gateway.sh paper
   netstat -tlnp | grep 4002
   ```

3. **Check learner state**:
   ```bash
   cat /home/davidsanker/platform/state/learner_state.json | jq .
   ```

### Timer Not Firing

1. **Check system time/timezone**:
   ```bash
   timedatectl
   ```

2. **Verify timers are enabled**:
   ```bash
   systemctl --user is-enabled trading-email-open.timer
   systemctl --user is-enabled trading-email-mid.timer
   systemctl --user is-enabled trading-email-close.timer
   ```

3. **Check next run time**:
   ```bash
   systemctl --user list-timers | grep email
   ```

---

## Email Report Contents

Each email includes:

1. **Timestamps** - Berlin time + UTC
2. **Gateway Health** - Validator status + API port check
3. **Services Status** - All trading services (ibgateway, bot services, watchdog)
4. **Active Bot Service** - Currently running bot service details
5. **Execution Gates** - DRY_RUN status, kill switch
6. **Portfolio Snapshot** - Net liquidation, cash, P&L, positions (top 8)
7. **Recent Executions** - Last 5 execution receipts
8. **Last VPA Decision** - Latest decision plan with confidence
9. **Learning State** - Last update, total trades, top 3 signal weights
10. **Incidents** - Count in last 24h + newest incident
11. **Next Action Hints** - Remediation steps if unhealthy

---

## Security Notes

⚠️ **IMPORTANT**:
- Never commit SMTP passwords to git
- Never include account IDs in logs
- Email config file should be readable only by owner: `chmod 600 config/email_report.env`
- SMTP password file must be `chmod 600`
- Reports redact sensitive information automatically

---

## Related Files

**Scripts**:
- `/home/davidsanker/platform/bin/generate_trading_email_report.py` - Report generator
- `/home/davidsanker/platform/bin/send_trading_email_report.sh` - Email sender
- `/home/davidsanker/platform/bin/send_email_smtp.py` - SMTP transport

**Config**:
- `/home/davidsanker/platform/config/email_report.env` - Email settings
- `~/.config/trading_mail/smtp_password` - SMTP credentials (not in repo)

**Systemd**:
- `~/.config/systemd/user/trading-email-open.{service,timer}`
- `~/.config/systemd/user/trading-email-mid.{service,timer}`
- `~/.config/systemd/user/trading-email-close.{service,timer}`

---

## Support

For issues or questions:
1. Check logs: `journalctl --user -u "trading-email*.service" --since "today"`
2. Review this documentation
3. Check artifacts: `/home/davidsanker/logs/email_scheduler_*`

---

**END OF DOCUMENTATION**
