# Quantum AI Trading Bot - Incident Response Runbook

**Version:** 0.1.0
**Last Updated:** January 24, 2026

---

## Table of Contents

1. [Emergency Procedures](#emergency-procedures)
2. [Common Incidents](#common-incidents)
3. [Diagnostic Commands](#diagnostic-commands)
4. [Recovery Procedures](#recovery-procedures)
5. [Escalation](#escalation)

---

## Emergency Procedures

### 🚨 IMMEDIATE HALT (Kill Switch)

**When to use:** Any unexpected behavior, large losses, or system runaway.

#### Option 1: Emergency Stop File (Fastest)

```bash
cd /path/to/quantum-trading-bot
touch EMERGENCY_STOP
```

The bot checks for this file before every trade and will halt immediately.

#### Option 2: Kill Processes

```bash
# Kill all trading bot processes
pkill -f quantum_trading_bot
pkill -f run_paper_production
pkill -f ibgateway

# Verify no processes remain
ps aux | grep -E "quantum|ibgateway"
```

#### Option 3: Stop Systemd Services

```bash
# Stop all services
systemctl --user stop quantum-trading-bot.service
systemctl --user stop quantum-trading-bot.timer
systemctl --user stop ib-gateway.service

# Verify stopped
systemctl --user status quantum-trading-bot
```

#### Option 4: Network Isolation (Nuclear Option)

```bash
# Block all IBKR traffic
sudo iptables -A OUTPUT -p tcp --dport 4002 -j DROP
sudo iptables -A OUTPUT -p tcp --dport 7497 -j DROP

# To unblock later
sudo iptables -D OUTPUT -p tcp --dport 4002 -j DROP
sudo iptables -D OUTPUT -p tcp --dport 7497 -j DROP
```

---

## Common Incidents

### Incident 1: IB Gateway Disconnection

**Symptoms:**
- Bot logs show "IB connection lost"
- `test_api_connection.py` fails
- No new trades being placed

**Diagnosis:**

```bash
# Check if IB Gateway is running
ps aux | grep ibgateway

# Check if port is listening
netstat -ltnp | grep 4002

# Check IB Gateway logs
tail -100 ~/IBGateway/latest/log.txt

# Test connection
python bin/test_api_connection.py
```

**Recovery:**

1. **If IB Gateway crashed:**

```bash
# Restart IB Gateway
~/IBGateway/latest/ibgateway &

# Wait 30 seconds
sleep 30

# Verify connection
python bin/test_api_connection.py
```

2. **If port conflict:**

```bash
# Find conflicting process
sudo lsof -i :4002

# Kill conflicting process
sudo kill -9 <PID>

# Restart IB Gateway
~/IBGateway/latest/ibgateway &
```

3. **If authentication failed:**

```bash
# Check for manual login requirement
test -f IB_GATEWAY_MANUAL_LOGIN_REQUIRED && echo "Manual login needed"

# Use IBC (IB Controller) for automated login
# See: ops/runbooks/IB_GATEWAY_AUTOMATION.md
```

**Prevention:**
- Use IBC for automated login and restart
- Configure keep-alive monitoring
- Set up alerts for disconnection

---

### Incident 2: Unexpected Losses

**Symptoms:**
- Large drawdown (>5% in single day)
- Multiple losing trades in a row
- Positions going against you rapidly

**Immediate Action:**

```bash
# EMERGENCY HALT
touch EMERGENCY_STOP
pkill -f quantum_trading_bot

# Close all positions (via TWS manually or API)
# DO NOT automate this - do it manually!
```

**Diagnosis:**

```bash
# Check recent trades
tail -50 state/ledgers/executions.jsonl

# Check open positions
python bin/ib_account_snapshot.py

# Check P&L
python bin/generate_trading_email_report.sh
```

**Analysis:**

1. **Review model performance:**

```bash
python bin/evaluate_model_zoo.py

# Check model calibration
python bin/score_calibration.py
```

2. **Check for regime change:**

```bash
python bin/regime_labeler.py
```

3. **Review risk parameters:**

```bash
# Check if risk limits were violated
grep -i "max_position" logs/paper_production.log | tail -20
```

**Recovery:**

1. **DO NOT restart trading immediately**
2. **Analyze what went wrong**
3. **Adjust risk parameters** (reduce position sizes, increase confidence thresholds)
4. **Test changes in dry-run mode** for at least 1 week
5. **Only then resume paper trading**

---

### Incident 3: System High Load / Memory Issues

**Symptoms:**
- Bot becomes unresponsive
- System load average >10
- Memory usage >90%
- Processes getting OOM killed

**Diagnosis:**

```bash
# Check system resources
htop

# Check memory usage
free -h

# Check disk space
df -h

# Check bot process stats
ps aux | grep quantum_trading_bot
```

**Immediate Action:**

```bash
# Stop the bot
touch EMERGENCY_STOP
pkill -f quantum_trading_bot

# Clear cache
echo 3 | sudo tee /proc/sys/vm/drop_caches
```

**Recovery:**

1. **Reduce resource usage:**

Edit `.env`:
```bash
MAX_WORKERS=2  # Reduce from 4
```

2. **Reduce trading universe:**

Edit `config/instruments.yaml`:
```yaml
# Comment out some symbols
# Reduce from 289 to ~50
```

3. **Enable data pruning:**

```bash
# Clean old logs
find logs/ -name "*.log" -mtime +7 -delete

# Clean old VPAs
find vpa_storage/ -name "*.json" -mtime +30 -delete
```

4. **Restart with monitoring:**

```bash
# Remove emergency stop
rm EMERGENCY_STOP

# Start with resource monitoring
/usr/bin/time -v python bin/run_paper_production.py
```

---

### Incident 4: Data Quality Issues

**Symptoms:**
- Models returning NaN or extreme values
- Obvious bad prices in data
- Failed backfills
- Missing data for key symbols

**Diagnosis:**

```bash
# Check data quality
python bin/unified_data_manager.py --check-quality

# Look for NaN in recent data
tail -100 logs/quantum-engine.log | grep -i "nan\|null\|error"

# Check data provider status
curl -I https://query1.finance.yahoo.com
```

**Recovery:**

1. **Restart data managers:**

```bash
# Clear data cache
rm -rf data/cache/*.pkl

# Restart bot
pkill -f quantum_trading_bot
python bin/run_paper_production.py
```

2. **Fallback to alternative data sources:**

Edit `config/quantum_runtime.env`:
```bash
# Enable fallback sources
ENABLE_YFINANCE_FALLBACK=true
```

3. **Skip problematic symbols:**

Edit `config/instruments.yaml`:
```yaml
# Comment out symbols with bad data
# - BBY  # Bad data as of 2026-01-24
```

---

### Incident 5: Model Degradation

**Symptoms:**
- Win rate declining over time
- Confidence scores dropping
- Model predictions no longer accurate

**Diagnosis:**

```bash
# Evaluate model performance
python bin/evaluate_model_zoo.py --period 7d

# Check calibration
python bin/score_calibration.py

# Review recent outcomes
tail -100 state/ledgers/outcomes.jsonl
```

**Recovery:**

1. **Retrain models with latest data:**

```bash
python bin/run_learning_update.py --force-retrain
```

2. **Reset calibration:**

```bash
rm -f learning/calibration_*.pkl
python bin/score_calibration.py --reset
```

3. **Disable underperforming models:**

Edit `config/model_zoo.yaml`:
```yaml
# Disable poorly performing models
models:
  phase1_ml_signal:
    enabled: false  # Disable if underperforming
```

4. **Fall back to simpler models:**

```bash
# Switch to EWMA baseline
export FORECAST_MODEL=ewma
export SIGNAL_MODEL=baseline_signal
```

---

## Diagnostic Commands

### System Health

```bash
# Overall system health
python bin/status_dashboard.sh

# Check all services
systemctl --user status quantum-trading-bot.*
systemctl --user status ib-gateway

# Check logs for errors
grep -i "error\|exception\|failed" logs/*.log | tail -50
```

### Trading Status

```bash
# Current positions
python bin/ib_account_snapshot.py

# Recent trades
tail -20 state/ledgers/executions.jsonl

# Pending orders
# (via TWS or API)

# P&L today
python bin/generate_trading_email_report.sh | grep "Today's P&L"
```

### Model Status

```bash
# Model zoo status
python bin/model_zoo_status.py

# Learning progress
python bin/learning_report.py

# Calibration status
python bin/score_calibration.py --summary
```

### IB Gateway

```bash
# Connection test
python bin/test_api_connection.py

# IB Gateway logs
tail -100 ~/IBGateway/latest/log.txt

# Port status
netstat -ltnp | grep 4002
```

---

## Recovery Procedures

### Full System Restart

```bash
#!/bin/bash
# Complete system restart script

echo "🔄 Starting full system restart..."

# 1. Stop everything
echo "⏹️  Stopping all services..."
touch EMERGENCY_STOP
pkill -f quantum_trading_bot
pkill -f ibgateway
systemctl --user stop quantum-trading-bot.*

# 2. Wait for cleanup
echo "⏳ Waiting for cleanup..."
sleep 10

# 3. Verify stopped
echo "✅ Verifying all processes stopped..."
if pgrep -f "quantum_trading_bot|ibgateway"; then
    echo "⚠️  Some processes still running, force killing..."
    pkill -9 -f quantum_trading_bot
    pkill -9 -f ibgateway
fi

# 4. Start IB Gateway
echo "🚀 Starting IB Gateway..."
~/IBGateway/latest/ibgateway &
sleep 30

# 5. Verify IB Gateway
echo "🔍 Verifying IB Gateway..."
if ! python bin/test_api_connection.py; then
    echo "❌ IB Gateway failed to start"
    exit 1
fi

# 6. Clear emergency stop
echo "🟢 Clearing emergency stop..."
rm -f EMERGENCY_STOP

# 7. Start trading bot
echo "🤖 Starting trading bot..."
systemctl --user start quantum-trading-bot.service

# 8. Verify started
echo "✅ Verifying trading bot..."
sleep 10
systemctl --user status quantum-trading-bot

echo "✅ System restart complete!"
```

### Configuration Rollback

```bash
# If a config change caused issues, roll back:

cd /path/to/quantum-trading-bot

# List recent config changes
git log --oneline config/

# Rollback to previous version
git checkout HEAD~1 -- config/model_zoo.yaml

# Restart bot
pkill -f quantum_trading_bot
systemctl --user restart quantum-trading-bot
```

### Data Recovery

```bash
# If ledgers get corrupted:

# 1. Stop bot
touch EMERGENCY_STOP

# 2. Backup corrupted data
cp state/ledgers/*.jsonl state/ledgers/backup_$(date +%Y%m%d_%H%M%S)/

# 3. Restore from last known good
cp state/ledgers/.backup_ledger_YYYYMMDD.jsonl state/ledgers/ledger.jsonl

# 4. Verify integrity
python -m json.tool state/ledgers/ledger.jsonl > /dev/null

# 5. Restart
rm EMERGENCY_STOP
systemctl --user restart quantum-trading-bot
```

---

## Escalation

### When to Escalate

- Losses >10% in single day
- Cannot diagnose issue after 1 hour
- System instability persists after restart
- Data corruption affecting ledgers
- Security incident (credentials leaked, etc.)

### Escalation Contacts

1. **Primary:** System Owner
2. **Secondary:** IBKR Support (for API issues)
3. **GitHub Issues:** https://github.com/Quantum-AI-Trading-Bot/issues

### Information to Collect

Before escalating, collect:

```bash
#!/bin/bash
# Incident data collection script

INCIDENT_DIR="logs/incident_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$INCIDENT_DIR"

# System info
uname -a > "$INCIDENT_DIR/system.txt"
free -h >> "$INCIDENT_DIR/system.txt"
df -h >> "$INCIDENT_DIR/system.txt"
uptime >> "$INCIDENT_DIR/system.txt"

# Process info
ps aux > "$INCIDENT_DIR/processes.txt"

# Recent logs (last 1000 lines)
tail -1000 logs/paper_production.log > "$INCIDENT_DIR/paper_production.log"
tail -1000 logs/quantum-engine.log > "$INCIDENT_DIR/quantum-engine.log"
tail -1000 logs/ib-connection.log > "$INCIDENT_DIR/ib-connection.log"

# IB Gateway logs
cp ~/IBGateway/latest/log.txt "$INCIDENT_DIR/ib_gateway.log"

# Configuration
cp .env "$INCIDENT_DIR/env.txt"  # REDACT SECRETS FIRST!
cp config/*.yaml "$INCIDENT_DIR/"

# State
cp state/ledgers/*.jsonl "$INCIDENT_DIR/"

# Model info
python bin/model_zoo_status.py > "$INCIDENT_DIR/model_status.txt"

echo "Incident data collected in: $INCIDENT_DIR"
```

---

## Post-Incident Procedures

### 1. Post-Mortem

Document:
- What happened
- When it happened
- Root cause
- Impact (financial and operational)
- Resolution steps
- Prevention measures

### 2. Update Runbooks

Add new incidents and procedures to this document.

### 3. Test Prevention Measures

Verify that new safeguards work before relying on them.

### 4. Share Learnings

Update GitHub wiki or discuss with community.

---

**Remember:** When in doubt, HALT TRADING FIRST, diagnose second. It's better to miss a trading opportunity than to lose money due to a technical issue.
