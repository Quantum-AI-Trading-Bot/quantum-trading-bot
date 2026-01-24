# Quantum AI Trading Bot - Quick Start Guide

**Last Updated:** January 24, 2026
**Version:** 0.1.0
**Status:** Paper Trading Ready

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [IB Gateway Setup](#ib-gateway-setup)
5. [Running Your First Cycle](#running-your-first-cycle)
6. [Enabling Paper Trading](#enabling-paper-trading)
7. [Next Steps](#next-steps)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **OS:** Linux (Debian 12+, Ubuntu 20.04+) or macOS 10.15+
- **Python:** 3.8 or higher (3.11 recommended)
- **RAM:** 8 GB minimum (16 GB recommended)
- **Storage:** 50 GB free space
- **Network:** Stable internet connection

### Required Accounts

1. **Interactive Brokers Account**
   - Paper trading account (free)
   - Live trading account (only after extensive testing)

2. **Data APIs** (Optional but Recommended)
   - Yahoo Finance (free, included)
   - News API (free tier available)
   - CoinGecko (free tier for crypto)

---

## Installation

### 1. Clone the Repository

```bash
cd ~
git clone https://github.com/Quantum-AI-Trading-Bot/quantum-trading-bot.git
cd quantum-trading-bot
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -e .
```

For development setup:

```bash
pip install -e ".[dev,learning,monitoring]"
```

### 4. Verify Installation

```bash
python -c "import quantum_trading_bot; print('✅ Installation successful')"
```

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit Configuration

```bash
nano .env  # Or use your preferred editor
```

**Minimum Required Settings:**

```bash
# Trading Mode (start with paper)
TRADING_MODE=paper

# IBKR Account
IBKR_ACCOUNT_ID=DU1234567  # Your paper trading account

# IB Connection
IB_HOST=127.0.0.1
IB_PORT=4002
CLIENT_ID=401

# Safety Settings (keep defaults!)
ALLOW_LIVE=false
TRADING_ENABLED=false
DRY_RUN=true
```

### 3. Create Required Directories

```bash
mkdir -p logs state/ledgers vpa_storage execution_receipts
```

---

## IB Gateway Setup

### What is IB Gateway?

IB Gateway is a lightweight application that allows the trading bot to communicate with Interactive Brokers. Unlike TWS (Trader Workstation), it has no GUI and is optimized for automated trading.

### Installation (Linux)

```bash
# Download IB Gateway
cd ~/Downloads
wget https://download.interactivebrokers.com/portal/latest/latest-standalone-linux-x64-v985+2.sh

# Install (follow the prompts)
chmod +x latest-standalone-linux-x64-v985+2.sh
./latest-standalone-linux-x64-v985+2.sh

# Install to default location: ~/IBGateway/latest
```

### Configuration

1. **Start IB Gateway manually first:**

```bash
~/IBGateway/latest/ibgateway &
```

2. **Configure Paper Trading:**
   - Log in with your paper trading account
   - Enable ActiveX/Socket clients
   - Set socket port to 4002 (paper trading)
   - Disable "Read-Only API" (unless testing)
   - Save configuration

3. **Test Connection:**

```bash
python bin/test_api_connection.py
```

Expected output:
```
✅ IB Gateway Connection: SUCCESS
Account: DU1234567
Mode: Paper Trading
```

### Automating IB Gateway Startup (Optional)

For production, you'll want IB Gateway to start automatically. See `ops/runbooks/IB_GATEWAY_AUTOMATION.md`.

---

## Running Your First Cycle

### Test Run (Dry Run Mode)

Dry run mode tests the entire pipeline without placing orders:

```bash
# Using the CLI
qbot-cycle --symbol SPY --dry-run

# Or using Python directly
python bin/run_one_cycle.py --symbol SPY
```

Expected output:
```
================================================================================
  QUANTUM AI TRADING BOT - SINGLE CYCLE
  Symbol: SPY
  Mode: DRY_RUN
================================================================================

🔄 Initializing Model Orchestrator...
📊 Loading market data...
🤖 Running forecast models...
📈 Generating signals...
💭 Decision: HOLD (confidence: 0.82)
✅ Cycle completed successfully
```

### What Just Happened?

1. **Data Collection:** Fetched historical data for SPY
2. **Forecasting:** Ran EWMA and ML models to predict direction
3. **Signal Generation:** Created buy/sell/hold signals
4. **Risk Assessment:** Checked position limits and portfolio risk
5. **Decision:** Made a trading decision (but didn't execute because of dry-run)

---

## Enabling Paper Trading

### Step 1: Enable Trading in Configuration

Edit `.env`:

```bash
# Enable paper trading (still safe!)
TRADING_MODE=paper
TRADING_ENABLED=true
DRY_RUN=false

# Keep live trading disabled!
ALLOW_LIVE=false
```

### Step 2: Start IB Gateway

```bash
# In one terminal
~/IBGateway/latest/ibgateway &
```

Wait 30 seconds for it to fully start.

### Step 3: Run Paper Production

```bash
# Using the CLI
qbot-paper-prod

# Or using the script
python bin/run_paper_production.py
```

### Step 4: Monitor

```bash
# In another terminal
watch -n 10 'tail -50 logs/paper_production.log'
```

### What to Expect

- The bot will run trading cycles every 2 minutes
- It will place PAPER trades (no real money)
- You'll see execution receipts in `execution_receipts/`
- VPAs (Verifiable Prediction Artifacts) in `vpa_storage/`

---

## Next Steps

### 1. Monitor Performance

After running for a few hours:

```bash
python bin/generate_trading_email_report.sh
```

This creates a performance report sent to your email (if configured).

### 2. Review Decisions

```bash
# View recent trading decisions
cat state/ledgers/decisions.jsonl | tail -20

# View VPA artifacts
ls -lh vpa_storage/ | tail -10
```

### 3. Run Learning Pipeline

```bash
python bin/run_learning_update.py
```

This retrains models with latest trade outcomes.

### 4. Enable Automated Scheduling

For continuous operation:

```bash
# Copy systemd service
cp ops/systemd/user/quantum-trading-bot.service ~/.config/systemd/user/

# Reload and start
systemctl --user daemon-reload
systemctl --user start quantum-trading-bot.timer
systemctl --user enable quantum-trading-bot.timer
```

---

## Troubleshooting

### Issue: "IB Gateway Not Connected"

**Symptoms:**
```
❌ IB Gateway Connection: FAILED
```

**Solutions:**
1. Check if IB Gateway is running:
   ```bash
   ps aux | grep ibgateway
   ```

2. Verify port:
   ```bash
   netstat -ltnp | grep 4002
   ```

3. Check IB Gateway logs:
   ```bash
   tail -100 ~/IBGateway/latest/log.txt
   ```

4. Ensure you're using paper trading port 4002 (not 7497)

### Issue: "Permission Denied" on Scripts

**Solution:**
```bash
chmod +x bin/*.sh
```

### Issue: "Module Not Found"

**Solution:**
```bash
# Ensure you installed the package in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Issue: "Out of Memory"

**Solution:**
1. Reduce the number of symbols in config
2. Limit max workers in `.env`:
   ```bash
   MAX_WORKERS=2
   ```

### Issue: "Trading Disabled"

**Symptoms:**
```
⚠️  TRADING_ENABLED=false - No trades will be executed
```

**Solution:**
Edit `.env` and set:
```bash
TRADING_ENABLED=true
```

**WARNING:** Only do this after thorough testing in dry-run mode!

---

## Safety Checklist

Before running with real money, ensure:

- [ ] Tested in paper trading for at least 2 weeks
- [ ] Positive returns in paper trading
- [ ] No bugs or errors in logs for 7+ days
- [ ] Understand all risk parameters
- [ ] Have emergency stop procedures in place
- [ ] Starting with minimum position sizes
- [ ] Have monitoring/alerting configured
- [ ] Read all documentation in `docs/`

---

## Getting Help

### Documentation
- `README.md` - Project overview
- `docs/architecture/` - System architecture
- `docs/ops/` - Operations guides
- `ops/runbooks/` - Incident response

### Community
- GitHub Issues: https://github.com/Quantum-AI-Trading-Bot/issues
- Discussions: https://github.com/Quantum-AI-Trading-Bot/discussions

### Emergency

To immediately stop all trading:

```bash
# Create emergency stop file
touch EMERGENCY_STOP

# Kill all bot processes
pkill -f quantum_trading_bot

# Stop systemd service
systemctl --user stop quantum-trading-bot.service
```

---

## Disclaimer

**This software is for educational purposes only. Trading stocks, options, and other financial instruments involves risk. Past performance does not guarantee future results.**

- Always start with paper trading
- Never risk more than you can afford to lose
- Understand the risks of automated trading
- Monitor your bot regularly
- Keep your credentials secure

**YOU ARE RESPONSIBLE FOR YOUR OWN TRADING DECISIONS AND LOSSES.**

---

**Congratulations!** You've completed the Quick Start Guide. Your Quantum AI Trading Bot is now running in paper trading mode. Monitor it closely, and good luck! 🚀
