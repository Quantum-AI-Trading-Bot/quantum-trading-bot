# Quantum AI Trading Bot - Dual-Track Deliverable Runbook

**Version**: 1.0
**Date**: January 15, 2026
**Status**: Production-Ready (Paper Trading)

---

## Executive Summary

This runbook delivers a **dual-track quantum AI trading system** with:

1. **Stable IB Gateway Foundation** - Automated watchdog with recovery
2. **Track A: MVP Bot** - Safe paper trading with risk guardrails
3. **Track B: Quantum Engine** - Verifiable prediction system
4. **Security Hardened** - Secrets removed, guardrails in place

**Current State**: ✅ Ready for paper trading deployment
**Live Trading**: ❌ Blocked by default (requires explicit override)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Dual-Track System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │ Track A: MVP │     │ Track B:     │                     │
│  │   Bot        │     │ Quantum      │                     │
│  │              │     │ Engine       │                     │
│  └──────┬───────┘     └──────┬───────┘                     │
│         │                    │                              │
│         └────────┬───────────┘                              │
│                  │                                          │
│                  ▼                                          │
│         ┌────────────────┐                                  │
│         │ Shared Gateway │                                  │
│         │   Validator    │                                  │
│         └────────┬───────┘                                  │
│                  │                                          │
│                  ▼                                          │
│         ┌────────────────┐                                  │
│         │ IB Gateway     │                                  │
│         │ Port 4002      │                                  │
│         └────────────────┘                                  │
│                  │                                          │
│                  ▼                                          │
│         ┌────────────────┐                                  │
│         │  Watchdog      │                                  │
│         │  (Auto-recover)│                                  │
│         └────────────────┘                                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Paper Trading)

### One-Command Startup

```bash
# Start complete stack (Track A: MVP Bot, Paper Mode)
/home/davidsanker/platform/bin/start_dual_track_stack.sh mvp paper
```

This single command:
1. ✅ Starts IB Gateway watchdog
2. ✅ Validates IB Gateway health
3. ✅ Waits for port 4002 (with manual login prompt if needed)
4. ✅ Starts MVP Bot in paper mode

### Alternative: Systemd Service

```bash
# Start via systemd
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
journalctl -u trading-bot -f
```

---

## Critical Safety Features

### 1. Paper Trading Enforcement

**Default Behavior**: System will NOT trade live money unless explicitly enabled.

```bash
# Paper trading (DEFAULT, SAFE)
TRADING_MODE=paper

# Live trading (BLOCKED unless ALLOW_LIVE=true)
TRADING_MODE=live ALLOW_LIVE=true  # Requires explicit override
```

### 2. Emergency Stop

```bash
# Immediately halt all trading
touch /home/davidsanker/platform/EMERGENCY_STOP

# Resume trading
rm /home/davidsanker/platform/EMERGENCY_STOP
```

Both tracks check for this file every cycle and stop immediately if present.

### 3. IB Gateway Authentication Required

Port 4002 will NOT listen until IB Gateway is authenticated. System will detect this and prompt for manual login:

```
═══════════════════════════════════════════════════════
  MANUAL LOGIN REQUIRED
═══════════════════════════════════════════════════════
1. Connect via VNC: vncviewer 35.232.64.211:5901
   or noVNC: http://35.232.64.211:6080/vnc.html
2. Complete IB Gateway authentication (2FA)
3. After login, API port 4002 should become active
4. Run: /home/davidsanker/platform/bin/validate_ib_gateway.sh
═══════════════════════════════════════════════════════
```

---

## Track A: MVP Bot (Safe Paper Trading)

### Purpose
Minimal viable trading bot with:
- ✅ Safe paper trading by default
- ✅ Risk management integration
- ✅ Pre-flight validation
- ✅ Emergency stop protection

### Start Commands

**Option 1: Direct script**
```bash
/home/davidsanker/platform/bin/run_mvp_bot.sh
```

**Option 2: Stack script**
```bash
/home/davidsanker/platform/bin/start_dual_track_stack.sh mvp paper
```

**Option 3: Systemd**
```bash
sudo systemctl start trading-bot-mvp
```

### Configuration

Edit `/home/davidsanker/platform/.env`:

```bash
# Trading mode (paper or live)
TRADING_MODE=paper

# Risk parameters
MAX_POSITION_SIZE=0.15      # 15% max per position
MAX_PORTFOLIO_RISK=0.25     # 25% portfolio volatility target
MAX_DAILY_LOSS_PCT=0.05     # 5% daily loss limit
MIN_CONFIDENCE=0.75         # 75% minimum confidence

# Trading enabled (default: false for safety)
TRADING_ENABLED=false       # Set true to enable order placement
```

### Logs

```bash
# Main log
tail -f /home/davidsanker/platform/logs/trading-bot/mvp_bot.log

# Output log
tail -f /home/davidsanker/platform/logs/trading-bot/mvp_bot_output.log
```

---

## Track B: Quantum Engine (Analysis & Prediction)

### Purpose
Advanced quantum-inspired prediction engine with:
- ✅ Verifiable Prediction Artifacts (VPA)
- ✅ Multi-timeframe analysis
- ✅ Risk metrics and decision plans
- ❌ NO trading unless explicitly enabled

### Start Commands

**Option 1: Direct script**
```bash
/home/davidsanker/platform/bin/run_quantum_engine.sh
```

**Option 2: Stack script**
```bash
/home/davidsanker/platform/bin/start_dual_track_stack.sh quantum paper
```

**Option 3: Systemd**
```bash
sudo systemctl start trading-bot-quantum
```

### Configuration

Edit `/home/davidsanker/platform/.env`:

```bash
# Quantum execution (default: false - analysis only)
QUANTUM_EXECUTION_ENABLED=false

# If true, will attempt to trade based on VPA decision_plan
# If false (default), generates VPA artifacts but does NOT trade
```

### VPA Artifacts

Track B generates **Verifiable Prediction Artifacts** in:
```
/home/davidsanker/platform/vpa_storage/
├── vpa_20260115_183000.json
├── vpa_20260115_183500.json
└── vpa_20260115_190000.json
```

Each VPA contains:
```json
{
  "timestamp": "2026-01-15T18:30:00+00:00",
  "track": "B",
  "mode": "false",
  "predictions": {
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "confidence": 0.85,
    "signal": "HOLD"
  },
  "risk_metrics": {
    "portfolio_var": 0.15,
    "max_drawdown": 0.08
  },
  "decision_plan": {
    "action": "NONE",
    "reason": "Analysis mode - no trading"
  }
}
```

---

## IB Gateway Management

### Watchdog (Automated Monitoring)

The IB Gateway watchdog runs continuously and:
- ✅ Checks gateway health every 30 seconds
- ✅ Auto-recovers from crashes
- ✅ Detects when authentication is needed
- ✅ Sets manual login flag when auth required

**Start watchdog:**
```bash
systemctl --user start ibgateway-watchdog.service
```

**Check status:**
```bash
systemctl --user status ibgateway-watchdog.service
```

**View logs:**
```bash
tail -f /home/davidsanker/platform/logs/ib-gateway/ib_watchdog.log
```

### Manual Recovery

If watchdog fails to recover:

```bash
# Run recovery script
/home/davidsanker/platform/bin/recover_ib_gateway.sh

# This will:
# 1. Start IB Gateway if not running
# 2. Wait for port 4002 (max 120s)
# 3. Attempt handshake
# 4. Set manual login flag if auth required
```

### Manual Login via VNC

**VNC Client:**
```bash
vncviewer 35.232.64.211:5901
```

**noVNC (Browser):**
```
http://35.232.64.211:6080/vnc.html
```

After login, remove manual login flag:
```bash
rm /home/davidsanker/platform/IB_GATEWAY_MANUAL_LOGIN_REQUIRED
```

---

## Validation & Health Checks

### Complete Stack Validation

```bash
/home/davidsanker/platform/bin/validate_dual_track_stack.sh
```

**Exit codes:**
- `0` = All healthy
- `1` = Gateway not healthy
- `2` = Bot not running
- `3` = Emergency stop detected

### IB Gateway Validation

```bash
/home/davidsanker/platform/bin/validate_ib_gateway.sh
```

**Exit codes:**
- `0` = Gateway OK (running + listening + handshake works)
- `2` = Process not running
- `3` = Port 4002 not listening
- `4` = Handshake/auth required
- `5` = Dependencies missing

### Port Verification

```bash
# Check if port 4002 is listening
ss -ltnp | grep 4002

# Should show:
# LISTEN 0 100 127.0.0.1:4002 0.0.0.0:* users:(("java",pid=...,fd=...))
```

---

## Troubleshooting

### Problem: Bot won't start

**Symptoms:**
```
Failed to load environment files: No such file or directory
```

**Solution:**
```bash
# Create .env from example
cp /home/davidsanker/platform/.env.example /home/davidsanker/platform/.env
chmod 640 /home/davidsanker/platform/.env

# Edit with your settings
nano /home/davidsanker/platform/.env
```

### Problem: Port 4002 not listening

**Symptoms:**
```
✗ Port 4002 not listening
```

**Solution:**
1. Connect via VNC and complete IB Gateway login
2. Wait 10-20 seconds for API to activate
3. Re-validate: `validate_ib_gateway.sh`

### Problem: Watchdog in crash loop

**Symptoms:**
```
Too many failures (3+), requiring manual login
```

**Solution:**
1. Remove manual login flag: `rm /home/davidsanker/platform/IB_GATEWAY_MANUAL_LOGIN_REQUIRED`
2. Connect via VNC and complete login
3. Restart watchdog: `systemctl --user restart ibgateway-watchdog`

### Problem: Emergency stop triggered

**Symptoms:**
```
EMERGENCY_STOP detected, shutting down
```

**Solution:**
```bash
# Check why emergency stop was triggered
cat /home/davidsanker/platform/EMERGENCY_STOP

# Remove to resume
rm /home/davidsanker/platform/EMERGENCY_STOP

# Restart bot
sudo systemctl start trading-bot
```

---

## Security & Secrets

### Secret Files Location

All secrets have been moved to:
```
/home/davidsanker/archives/secrets_20260115_185708/
├── api_keys.json
├── backup_config.ini
├── backup_jts.ini
└── ibc-config.ini
```

### Example Files

To configure the system, use example files:
```bash
# Environment variables
cp /home/davidsanker/platform/.env.example /home/davidsanker/platform/.env

# API keys (for external data sources)
cp /home/davidsanker/platform/config/api_keys.example.json /home/davidsanker/platform/config/api_keys.json

# IBC config
cp /home/davidsanker/platform/ibc-config.example.ini /home/davidsanker/platform/ibc-config.ini
```

**⚠️ IMPORTANT**: Never commit `.env` or secret files to version control!

### .gitignore

The `.gitignore` file is configured to block:
- `.env`
- `config/api_keys.json`
- `config/backup_*.ini`
- `ibc-config.ini`
- `EMERGENCY_STOP`
- Log files

---

## Acceptance Tests

### Test Suite

Run all acceptance tests:

```bash
cd /home/davidsanker/platform/docs

# Test 1: Stack validation
./01_acceptance_tests.sh
```

### Manual Verification

**Test 1: Gateway Validation**
```bash
/home/davidsanker/platform/bin/validate_ib_gateway.sh
# Expected: Exit code 0 (if gateway ready) or 4 (if auth needed)
```

**Test 2: Port Listening**
```bash
ss -ltnp | grep 4002
# Expected: Port 4002 listening (after manual login)
```

**Test 3: VPA Creation (Track B)**
```bash
# Start quantum engine
/home/davidsanker/platform/bin/run_quantum_engine.sh &
# Wait 30 seconds, then check:
ls -la /home/davidsanker/platform/vpa_storage/
# Expected: vpa_*.json artifacts created
```

**Test 4: Bot Start (Track A)**
```bash
# Start MVP bot
/home/davidsanker/platform/bin/run_mvp_bot.sh &
# Wait 10 seconds, then check:
ps aux | grep quantum_trading_bot
# Expected: Bot process running
```

**Test 5: Emergency Stop**
```bash
# Start bot in background
/home/davidsanker/platform/bin/run_mvp_bot.sh &
BOT_PID=$!

# Trigger emergency stop
touch /home/davidsanker/platform/EMERGENCY_STOP

# Wait and check
sleep 5
ps -p $BOT_PID
# Expected: Process not running (stopped by emergency stop)
rm /home/davidsanker/platform/EMERGENCY_STOP
```

---

## Systemd Services

### Available Services

```bash
# Main service (MVP track, enabled by default)
trading-bot.service

# Track-specific services
trading-bot-mvp.service       # MVP Bot only
trading-bot-quantum.service   # Quantum Engine only

# Gateway watchdog (user service)
ibgateway-watchdog.service    # Runs under user systemd
```

### Service Management

```bash
# System services (sudo required)
sudo systemctl start trading-bot
sudo systemctl stop trading-bot
sudo systemctl restart trading-bot
sudo systemctl status trading-bot
sudo systemctl enable trading-bot   # Auto-start on boot
sudo systemctl disable trading-bot  # Don't auto-start

# User services (no sudo)
systemctl --user start ibgateway-watchdog
systemctl --user stop ibgateway-watchdog
systemctl --user status ibgateway-watchdog
systemctl --user enable ibgateway-watchdog
```

---

## Logging

### Log Locations

```
/home/davidsanker/platform/logs/
├── ib-gateway/
│   ├── ib_watchdog.log
│   ├── recovery.log
│   └── auto_recovery.log
├── trading-bot/
│   ├── mvp_bot.log
│   ├── mvp_bot_output.log
│   └── service.log
├── quantum-engine/
│   ├── quantum_engine.log
│   └── quantum_service.log
└── healthchecks/
```

### Log Rotation

Logs are rotated daily:
- Keep 14 days for general logs
- Keep 30 days for critical logs (gateway, trading, quantum)
- Compressed after rotation

**Manual log rotation test:**
```bash
sudo logrotate -d /etc/logrotate.d/platform
```

---

## File Structure

```
/home/davidsanker/platform/
├── bin/                          # Executable scripts
│   ├── start_dual_track_stack.sh  # MAIN ENTRY POINT
│   ├── run_mvp_bot.sh            # Track A: MVP Bot
│   ├── run_quantum_engine.sh      # Track B: Quantum Engine
│   ├── validate_ib_gateway.sh     # Gateway validator
│   ├── recover_ib_gateway.sh      # Gateway recovery
│   ├── watchdog_ib_gateway.sh     # Gateway watchdog
│   ├── validate_dual_track_stack.sh  # Stack validator
│   └── emergency_stop.sh         # Emergency stop
├── config/                       # Configuration files
│   ├── .env.example              # Environment template
│   ├── api_keys.example.json     # API keys template
│   └── ibc-config.example.ini    # IBC config template
├── logs/                         # Log directories
│   ├── ib-gateway/
│   ├── trading-bot/
│   ├── quantum-engine/
│   └── healthchecks/
├── vpa_storage/                  # VPA artifacts (Track B)
├── docs/
│   └── DELIVERABLE_RUNBOOK.md    # This file
├── .env                          # Environment (CREATE FROM EXAMPLE)
├── .gitignore                    # Git ignore rules
└── logrotate_platform.conf       # Log rotation config
```

---

## Changed Files Summary

### New Files Created

1. **IB Gateway Foundation**
   - `/home/davidsanker/platform/bin/validate_ib_gateway.sh`
   - `/home/davidsanker/platform/bin/recover_ib_gateway.sh`
   - `/home/davidsanker/platform/bin/watchdog_ib_gateway.sh`
   - `~/.config/systemd/user/ibgateway-watchdog.service`

2. **Dual-Track Scripts**
   - `/home/davidsanker/platform/bin/start_dual_track_stack.sh`
   - `/home/davidsanker/platform/bin/run_mvp_bot.sh`
   - `/home/davidsanker/platform/bin/run_quantum_engine.sh`
   - `/home/davidsanker/platform/bin/validate_dual_track_stack.sh`

3. **Security Files**
   - `/home/davidsanker/platform/.env` (from .env.example)
   - `/home/davidsanker/platform/.env.example`
   - `/home/davidsanker/platform/.gitignore`
   - `/home/davidsanker/platform/config/api_keys.example.json`
   - `/home/davidsanker/platform/ibc-config.example.ini`

4. **Systemd Services**
   - `/etc/systemd/system/trading-bot.service` (updated)
   - `/etc/systemd/system/trading-bot.service.backup`
   - `/etc/systemd/system/trading-bot-mvp.service` (new)
   - `/etc/systemd/system/trading-bot-quantum.service` (new)

5. **Logging**
   - `/home/davidsanker/platform/logrotate_platform.conf`
   - Log directories created

6. **Documentation**
   - `/home/davidsanker/platform/docs/DELIVERABLE_RUNBOOK.md` (this file)

### Files Moved to Archives

**Secrets** (not deleted, just archived):
```
/home/davidsanker/archives/secrets_20260115_185708/
├── api_keys.json
├── backup_config.ini
├── backup_jts.ini
└── ibc-config.ini
```

**Deprecated Scripts**:
```
/home/davidsanker/platform/tools/legacy/
├── ib_web_automation_login.py (with deprecation header)
├── manual_ib_auth.sh (with deprecation header)
└── daily_auth_window.sh (with deprecation header)
```

---

## Next Steps

### Immediate Actions Required

1. **Configure Environment**
   ```bash
   nano /home/davidsanker/platform/.env
   # Add your IBKR account ID and preferences
   ```

2. **Complete Manual IB Gateway Login**
   ```bash
   # Connect via VNC
   vncviewer 35.232.64.211:5901
   # Complete 2FA authentication
   # Wait for port 4002 to open
   ```

3. **Validate System**
   ```bash
   /home/davidsanker/platform/bin/validate_dual_track_stack.sh
   ```

4. **Start Paper Trading**
   ```bash
   /home/davidsanker/platform/bin/start_dual_track_stack.sh mvp paper
   ```

### Monitoring

Once running:

```bash
# Check bot status
tail -f /home/davidsanker/platform/logs/trading-bot/mvp_bot.log

# Check gateway health
watch -n 10 '/home/davidsanker/platform/bin/validate_ib_gateway.sh'

# System status
/home/davidsanker/platform/bin/status_dashboard.sh
```

---

## Contact & Support

**System Owner**: David Sanker
**Implementation**: Claude Code
**Date**: January 15, 2026
**Baseline Artifacts**: `/home/davidsanker/logs/dual_track_bootstrap_20260115_183743/`

---

## Appendix: Commands Reference

### Essential Commands

| Action | Command |
|--------|---------|
| Start stack (MVP) | `/home/davidsanker/platform/bin/start_dual_track_stack.sh mvp paper` |
| Start stack (Quantum) | `/home/davidsanker/platform/bin/start_dual_track_stack.sh quantum paper` |
| Validate stack | `/home/davidsanker/platform/bin/validate_dual_track_stack.sh` |
| Validate gateway | `/home/davidsanker/platform/bin/validate_ib_gateway.sh` |
| Emergency stop | `touch /home/davidsanker/platform/EMERGENCY_STOP` |
| Clear emergency | `rm /home/davidsanker/platform/EMERGENCY_STOP` |
| Start watchdog | `systemctl --user start ibgateway-watchdog` |
| Check watchdog | `systemctl --user status ibgateway-watchdog` |

### Verification Commands

```bash
# Check port 4002
ss -ltnp | grep 4002

# Check gateway process
ps aux | grep -i ibgateway

# Check bot process
ps aux | grep quantum_trading_bot

# Check VPA artifacts
ls -la /home/davidsanker/platform/vpa_storage/

# View watchdog logs
tail -f /home/davidsanker/platform/logs/ib-gateway/ib_watchdog.log

# View bot logs
tail -f /home/davidsanker/platform/logs/trading-bot/mvp_bot.log
```

---

**END OF RUNBOOK**
