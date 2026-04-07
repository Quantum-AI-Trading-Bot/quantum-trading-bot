# Autonomous Paper Trading Runbook

**Deployment Date:** 2026-01-26 (Monday Target)
**System:** Quantum AI Trading Bot
**Mode:** PAPER TRADING ONLY (NEVER LIVE)
**Branch:** `autonomous-paper-exec-authority-20260126`

---

## 🚨 CRITICAL SAFETY RULES (READ FIRST)

### HARD NON-NEGOTIABLES
1. **ALLOW_LIVE=false** - Live trading is HARD BANNED
2. **IB_PORT=4002** - Paper trading port ONLY (never 7497)
3. **EMERGENCY_STOP** - File existence halts ALL trading
4. **Fail-Closed** - Any uncertainty blocks execution

### INSTANT SHUTDOWN
```bash
# To immediately halt all trading:
touch ~/platform/EMERGENCY_STOP

# To resume (after verifying safety):
rm ~/platform/EMERGENCY_STOP
```

---

## 📋 SYSTEM ARCHITECTURE

### 8-Step Safety Gating (Order Placement)

Every order passes through ALL gates before transmission:

```
GATE 0: ALLOW_LIVE check (HARD BAN if true)
GATE 1: EMERGENCY_STOP file check
GATE 2: Paper account proof (port 4002 + account type)
GATE 3: Execution Authority (time windows + kill switch)
GATE 4: Whitelist check (symbol + asset class)
GATE 5: Risk Manager (exposure + limits)
GATE 6: Pilot Guardrails (legacy compatibility)
GATE 7: Market Open check (payload-validation if closed)
```

**Only if ALL 8 gates pass** → Order placed (paper account)

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Execution Authority | `engine/execution_authority.py` | Time-based trading windows |
| Whitelist Manager | `engine/whitelist.py` | Asset/symbol rollout control |
| Risk Manager | `engine/risk_manager.py` | Portfolio risk limits |
| VPA Executor | `bin/vpa_executor.py` | Order execution with 8 gates |
| Watchdog | `bin/execution_watchdog.py` | System health monitoring |
| Reconcile | `bin/reconcile_broker_state.py` | Broker state reconciliation |
| Status | `bin/trading_status.py` | One-screen dashboard |

---

## 🔧 CONFIGURATION FILES

### 1. Runtime Configuration
**File:** `config/quantum_runtime.env`

```bash
# Autonomous mode (DO NOT CHANGE)
ALLOW_LIVE=false                    # LIVE TRADING IS FORBIDDEN
PAPER_EXECUTION_MODE=true           # Paper trading ONLY
IB_PORT=4002                        # Paper trading port
REQUIRE_PAPER_PROOF=true            # Must validate paper account

# Execution authority
WHITELIST_PROFILE=phase0_stocks_us  # Starting profile
EXECUTION_AUTHORITY_TIMEZONE=Europe/Berlin
EXECUTION_TRANSMIT_WHEN_CLOSED=false  # Don't transmit when market closed

# Safety
QUANTUM_EXECUTION_DRY_RUN=false     # Disabled for autonomy
```

### 2. Risk Limits
**File:** `config/risk_limits.yaml`

```yaml
max_gross_exposure_usd: 250000      # 25% of 1M portfolio
max_net_exposure_usd: 150000        # 15% net long/short
max_daily_loss_usd: 5000            # 0.5% daily loss limit
max_drawdown_usd: 25000             # 2.5% drawdown limit
max_position_usd_per_symbol: 50000  # 5% max per symbol
max_order_notional_usd: 25000       # 2.5% max single order
max_orders_per_day_global: 50
```

### 3. Whitelist Profiles
**Directory:** `config/whitelists/`

**Phase 0 (Initial):** `phase0_stocks_us.yaml`
- Asset classes: STOCK, ETF
- Symbols: SPY, QQQ, IWM, DIA, AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA
- Max orders/day: 20
- Max position: $50,000/symbol

**Phase 1 (Add Options):** `phase1_add_options_defined_risk.yaml`
- Asset classes: STOCK, ETF, OPTION
- Options: Long only, no short premium
- Max premium/day: $2,000
- Max contracts/order: 2

**Phase 2 (Add Futures):** `phase2_add_micro_futures.yaml`
- Asset classes: STOCK, ETF, OPTION, FUT
- Futures: Micro only (MES, MNQ)
- Max contracts/order: 1

### 4. Execution Authority
**File:** `config/execution_authority.yaml`

```yaml
mode: autonomous
timezone: Europe/Berlin
windows:
  - days: [Mon, Tue, Wed, Thu, Fri]
    start: "09:30"
    end: "22:00"
allow_weekends: false
require_paper_proof: true
kill_switch_file: "EMERGENCY_STOP"
```

---

## 🚀 DEPLOYMENT PROCEDURE (Monday 2026-01-26)

### Pre-Deployment Checklist

```bash
# 1. Verify we're on correct branch
cd ~/platform
git branch
# Should show: * autonomous-paper-exec-authority-20260126

# 2. Verify ALLOW_LIVE is false
grep "ALLOW_LIVE" config/quantum_runtime.env
# Should show: ALLOW_LIVE=false

# 3. Verify IB port
grep "IB_PORT" config/quantum_runtime.env
# Should show: IB_PORT=4002

# 4. Check EMERGENCY_STOP doesn't exist
ls EMERGENCY_STOP 2>/dev/null && echo "🚨 EMERGENCY_STOP EXISTS - ABORT" || echo "✓ OK"
```

### Step 1: Validate Paper Account

```bash
# Run paper account assertion (creates proof file)
cd ~/platform
python3 bin/assert_paper_account.py

# Should create: state/paper_account_ok.txt
cat state/paper_account_ok.txt
```

### Step 2: Validate All Modules

```bash
# Test execution authority
python3 engine/execution_authority.py

# Test whitelist
python3 engine/whitelist.py --symbol SPY --asset-class ETF

# Test risk manager
python3 engine/risk_manager.py --equity 1000000 --symbol SPY --side BUY --qty 100 --price 450
```

### Step 3: Start IB Gateway (Paper Trading)

```bash
# Ensure IBC is running with paper trading configuration
# Connect to port 4002 (paper trading)
# Verify connection:
ss -ltnp | grep 4002
```

### Step 4: Run Canary Validation

```bash
# Run VPA executor in dry-run mode first
cd ~/platform
python3 bin/vpa_executor.py --dry-run true

# Should see:
# - All 8 gates checked
# - Order validation but NO transmission
# - Receipt saved to execution_receipts/
```

### Step 5: Enable Autonomous Mode

```bash
# Edit quantum_runtime.env
# Set: QUANTUM_EXECUTION_DRY_RUN=false
# Set: WHITELIST_PROFILE=phase0_stocks_us

# Reload watchdog
systemctl --user restart trading-watchdog.service
```

### Step 6: Monitor System

```bash
# Watch status (real-time)
watch -n 5 ~/platform/bin/trading_status.py

# Or continuous mode:
~/platform/bin/trading_status.py --watch
```

---

## 📊 MONITORING

### Quick Status Check

```bash
~/platform/bin/trading_status.py
```

**Shows:**
- EMERGENCY_STOP status
- Execution authority status
- Whitelist profile
- Risk manager state
- IB Gateway status
- Recent execution receipts
- Systemd service status

### Health Checks

```bash
# Run watchdog health checks
~/platform/bin/execution_watchdog.py

# Continuous monitoring (every 60s)
~/platform/bin/execution_watchdog.py --continuous
```

### Broker Reconciliation

```bash
# Reconcile broker state vs ledgers
~/platform/bin/reconcile_broker_state.py
```

### View Receipts

```bash
# List recent receipts
ls -lt ~/platform/execution_receipts/ | head -20

# View a specific receipt
cat ~/platform/execution_receipts/20260126_*.json | jq .
```

### View Logs

```bash
# Execution log
tail -f ~/platform/logs/quantum-engine/execution.log

# Watchdog log
tail -f ~/platform/logs/watchdog/watchdog.log

# Reconcile log
tail -f ~/platform/logs/quantum-engine/reconcile.log
```

---

## 🛠️ TROUBLESHOOTING

### Problem: Orders Not Being Placed

**Check 1: EMERGENCY_STOP**
```bash
ls ~/platform/EMERGENCY_STOP
# If exists, trading is halted
```

**Check 2: Execution Authority**
```bash
python3 engine/execution_authority.py
# Check if "allowed": true
# Check reason_code if blocked
```

**Check 3: Whitelist**
```bash
python3 engine/whitelist.py --symbol SPY
# Check if symbol is allowed
```

**Check 4: Risk Manager**
```bash
python3 engine/risk_manager.py --equity 1000000 --symbol SPY --side BUY --qty 100 --price 450
# Check if risk limits allow order
```

**Check 5: IB Gateway**
```bash
pgrep -f ibgateway
ss -ltnp | grep 4002
```

### Problem: "ALLOW_LIVE=true" Error

**Solution:**
```bash
# Edit config/quantum_runtime.env
nano ~/platform/config/quantum_runtime.env
# Set: ALLOW_LIVE=false

# Remove EMERGENCY_STOP if created
rm ~/platform/EMERGENCY_STOP
```

### Problem: Market Closed - Orders Not Transmitting

**This is expected behavior!** When market is closed:
- Orders pass all gates except GATE 7 (Market Open)
- Receipts show status: `PAYLOAD_VALIDATION_ONLY`
- Reason: `MARKET_CLOSED`
- **Orders are NOT transmitted** (correct behavior)

**To override (NOT RECOMMENDED):**
```bash
# Edit config/quantum_runtime.env
# Set: EXECUTION_TRANSMIT_WHEN_CLOSED=true
```

### Problem: Risk Manager Blocking Orders

**Check state:**
```bash
cat ~/platform/state/risk_state.json | jq .
```

**Reset daily counters (if needed):**
```bash
# Edit state/risk_state.json
# Set: "orders_today": 0
# Set: "daily_loss_usd": 0
```

---

## 🔄 ROLLBACK PROCEDURE

If you need to rollback to manual mode:

```bash
# 1. Stop autonomous trading
touch ~/platform/EMERGENCY_STOP

# 2. Enable dry-run mode
nano ~/platform/config/quantum_runtime.env
# Set: QUANTUM_EXECUTION_DRY_RUN=true

# 3. Stop systemd services
systemctl --user stop trading-paper-production.service
systemctl --user stop trading-watchdog.service

# 4. Switch to previous branch
git checkout main

# 5. Restart with manual control
```

---

## 📈 PHASE ROLLPLAN (Graduated Asset Rollout)

### Current Phase: Phase 0 (Starting Monday)
- **Profile:** `phase0_stocks_us`
- **Assets:** US Stocks + ETFs only
- **Symbols:** 10 blue-chip stocks/ETFs
- **Duration:** 1-2 weeks

### Phase 1: Add Options (After Phase 0 Stable)
- **Profile:** `phase1_add_options_defined_risk`
- **Assets:** Stocks + ETFs + Long Options
- **Restrictions:** No short premium, no spreads
- **Duration:** 2-3 weeks

### Phase 2: Add Micro Futures (After Phase 1 Stable)
- **Profile:** `phase2_add_micro_futures`
- **Assets:** Stocks + ETFs + Options + Micro Futures
- **Restrictions:** Micro contracts only, max 1 contract/order
- **Duration:** Ongoing

**To Advance Phase:**
```bash
# Edit config/quantum_runtime.env
nano ~/platform/config/quantum_runtime.env
# Change: WHITELIST_PROFILE=phase1_add_options_defined_risk

# Reload watchdog
systemctl --user reload trading-watchdog.service
```

---

## ✅ READINESS CHECKLIST (Monday Morning)

- [ ] Branch: `autonomous-paper-exec-authority-20260126`
- [ ] ALLOW_LIVE=false
- [ ] IB_PORT=4002
- [ ] Paper account proof exists (`state/paper_account_ok.txt`)
- [ ] IB Gateway running on port 4002
- [ ] EMERGENCY_STOP does NOT exist
- [ ] Risk limits configured (`config/risk_limits.yaml`)
- [ ] Whitelist profile selected (`phase0_stocks_us`)
- [ ] Canary validation passed
- [ ] Watchdog service running
- [ ] Status command working

**Final Command Before Going Autonomous:**
```bash
~/platform/bin/trading_status.py
```

All checks should show ✓ (green).

---

## 📞 CONTACT & SUPPORT

**Runbook Version:** 1.0
**Last Updated:** 2026-01-24
**Author:** Claude Code (Autonomous Trading System)

**For Issues:**
1. Check logs: `~/platform/logs/`
2. Check receipts: `~/platform/execution_receipts/`
3. Run status: `~/platform/bin/trading_status.py`
4. Create EMERGENCY_STOP if critical

**REMEMBER:** This is PAPER TRADING ONLY. Never allow live trading.
