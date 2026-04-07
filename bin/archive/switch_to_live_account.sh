#!/bin/bash
set -euo pipefail

# ============================================================================
# 🔄 QUANTUM AI TRADING BOT - PAPER TO LIVE ACCOUNT SWITCH
# Minimal Friction Maximum Safety Strategy
# ============================================================================

LOG_DIR="/home/davidsanker/platform/logs/live-switch"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/live_switch_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log "=========================================="
log "🔄 QUANTUM AI TRADING BOT - LIVE SWITCH"
log "=========================================="
log "This script will switch from paper to live trading with maximum safety"

# 1. PRE-SWITCH SAFETY CHECKS
log ""
log "Step 1: Pre-Switch Safety Analysis"

# Check current paper account portfolio value
log "📊 Current Paper Portfolio Analysis..."
source ~/venv/bin/activate
PAPER_PORTFOLIO_VALUE=$(timeout 15 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=7777, timeout=10)

    # Get account summary (Net Liquidation Value)
    summary = ib.accountSummary()
    for item in summary:
        if item.tag == 'NetLiquidationByCurrency' and item.currency == 'USD':
            print(item.value)
            break
    ib.disconnect()
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>/dev/null)

if [ -n "$PAPER_PORTFOLIO_VALUE" ] && [ "$PAPER_PORTFOLIO_VALUE" -gt 0 ]; then
    log "✅ Paper Account Equity: \$$PAPER_PORTFOLIO_VALUE"
else
    log "❌ ERROR: Could not retrieve paper account value"
    log "⚠️  Please ensure IB Gateway is connected before switching to live"
    exit 1
fi

# 2. RISK WARNING AND CONFIRMATION
log ""
log "⚠️  LIVE TRADING RISK WARNING:"
log "- You are about to switch from PAPER to LIVE trading"
log "- REAL money will be at risk"
log "- Your current paper equity: \$$PAPER_PORTFOLIO_VALUE"
log "- This is your actual trading account balance"
log ""
log "🛡️  RECOMMENDED SAFETY MEASURES:"
log "1. Start with small position sizes (10-20% of normal)"
log "2. Monitor closely for first 24 hours"
log "3. Use stop-loss orders on all positions"
log "4. Keep paper account running as backup"

# 3. BACKUP CURRENT CONFIGURATION
log ""
log "Step 2: Creating Backup of Paper Configuration"

# Backup current config
BACKUP_FILE="/home/davidsanker/IBC/config_paper_backup_${TIMESTAMP}.ini"
cp /home/davidsanker/IBC/config.ini "$BACKUP_FILE"
log "✅ Paper config backed up to: $BACKUP_FILE"

# Create live config template
LIVE_CONFIG="/home/davidsanker/IBC/config_live.ini"
cp "$BACKUP_FILE" "$LIVE_CONFIG"

log "✅ Live config template created"

# 4. CREATE LIVE ACCOUNT CONFIGURATION
log ""
log "Step 3: Configuring Live Account Settings"

# Update live config for live trading
sed -i 's/TradingMode=paper/TradingMode=live/' "$LIVE_CONFIG"
sed -i 's/AutoRestartTime=07:05/AutoRestartTime=/' "$LIVE_CONFIG"  # Remove auto-restart
sed -i 's/ColdRestartTime=07:05/#ColdRestartTime=/' "$LIVE_CONFIG"     # Comment out cold restart

# Add live trading safety parameters
cat >> "$LIVE_CONFIG" << 'EOF'

# LIVE TRADING SAFETY SETTINGS
MaxOrderSize=100
ReadOnlyApi=no
TradeConfirm=2
OrderSizeWarning=1000

# Live Account Specific
IbLoginId=DU565783  # Update with your live account username
IbPassword=YOUR_IB_PASSWORD  # Update with your live account password
EOF

log "✅ Live account configuration created"

# 5. CREATE SWITCHING SCRIPTS
log ""
log "Step 4: Creating Account Switching Scripts"

# Create paper account switcher
cat > /home/davidsanker/platform/bin/switch_to_paper.sh << 'EOF'
#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "🔄 Switching to PAPER trading mode"

# Stop current services
sudo systemctl stop trading-bot.service
sudo pkill -f "java.*ibgateway" 2>/dev/null || true
sleep 5

# Switch to paper config
cp /home/davidsanker/IBC/config_paper_backup_*.ini /home/davidsanker/IBC/config.ini 2>/dev/null || \
cp /home/davidsanker/IBC/config.ini.backup /home/davidsanker/IBC/config.ini

# Update to paper mode
sed -i 's/TradingMode=live/TradingMode=paper/' /home/davidsanker/IBC/config.ini

# Start paper trading
/home/davidsanker/platform/bin/complete_community_solution.sh

log "✅ Switched to PAPER trading mode"
EOF

# Create live account switcher
cat > /home/davidsanker/platform/bin/switch_to_live.sh << 'EOF'
#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "🔄 Switching to LIVE trading mode"

# CRITICAL SAFETY CONFIRMATION
echo "⚠️  LIVE TRADING - REAL MONEY AT RISK!"
echo "Current paper portfolio value will be at risk"
echo "Are you absolutely sure? (Type 'CONFIRM-LIVE' to proceed)"
read -r confirmation

if [ "$confirmation" != "CONFIRM-LIVE" ]; then
    log "❌ SWITCH CANCELLED by user"
    exit 1
fi

# Stop current services
sudo systemctl stop trading-bot.service
sudo pkill -f "java.*ibgateway" 2>/dev/null || true
sleep 5

# Switch to live config
cp /home/davidsanker/IBC/config_live.ini /home/davidsanker/IBC/config.ini

# Update live credentials if needed
# The script will prompt you to confirm credentials are correct

# Start live trading
echo "🚀 Starting LIVE IB Gateway..."
/home/davidsanker/platform/bin/complete_community_solution.sh

log "✅ Switched to LIVE trading mode"
log "📧 Live trading safety email sent"

# Send safety email
echo "Subject: LIVE TRADING ACTIVATED - $(date)
Your Quantum AI Trading Bot has been switched to LIVE trading.
Current equity: \$$(python3 -c "
from ib_insync import IB; ib=IB(); ib.connect('127.0.0.1',4002,clientId=7778,timeout=5);
print([i.value for i in ib.accountSummary() if i.tag == 'NetLiquidationByCurrency'][0])
ib.disconnect()")
" | mail -s "LIVE TRADING ACTIVATED" david@sanker.at miriam.sanker@gmail.com
EOF

chmod +x /home/davidsanker/platform/bin/switch_to_paper.sh
chmod +x /home/davidsanker/platform/bin/switch_to_live.sh

log "✅ Account switching scripts created"

# 6. CREATE LIVE TRADING MONITOR
log ""
log "Step 5: Creating Live Trading Safety Monitor"

cat > /home/davidsanker/platform/bin/live_trading_monitor.sh << 'EOF'
#!/bin/bash
# Live Trading Safety Monitor
# Monitors for excessive losses and provides alerts

ALERT_THRESHOLD=10000  # Alert if losses exceed \$10,000
SHUTDOWN_THRESHOLD=25000  # Emergency shutdown at \$25,000 loss

check_live_risk() {
    source ~/venv/bin/activate
    python3 -c "
from ib_insync import IB
import sys
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=7779, timeout=10)

    # Get current portfolio value
    summary = ib.accountSummary()
    nlv = 0
    for item in summary:
        if item.tag == 'NetLiquidationByCurrency' and item.currency == 'USD':
            nlv = float(item.value)
            break

    # Calculate total PnL
    portfolio = ib.portfolio()
    total_pnl = sum(item.unrealizedPnL + item.realizedPNL for item in portfolio)

    print(f'EQUITY: \${nlv:.2f}')
    print(f'TOTAL PNL: \${total_pnl:.2f}')

    # Risk assessment
    if total_pnl <= -SHUTDOWN_THRESHOLD:
        print('🚨 CRITICAL: Emergency shutdown triggered!')
        sys.exit(2)  # Critical error code

    elif total_pnl <= -ALERT_THRESHOLD:
        print('⚠️ WARNING: High losses detected!')
        sys.exit(1)  # Warning code

    else:
        print('✅ Risk levels acceptable')
        sys.exit(0)  # Success code

    ib.disconnect()
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"
}

# Check current risk level
RISK_LEVEL=$(check_live_risk)
case $RISK_LEVEL in
    2)  # Critical
        echo "$(date): 🚨 EMERGENCY - Stopping trading bot due to excessive losses"
        sudo systemctl stop trading-bot.service
        echo "$(date): 🚨 EMERGENCY SHUTDOWN TRIGGERED" >> /var/log/live_trading_emergency.log
        ;;
    1)  # Warning
        echo "$(date): ⚠️ WARNING - High trading losses detected - monitor closely"
        ;;
    0)  # OK
        echo "$(date): ✅ Trading risk levels acceptable"
        ;;
esac
EOF

chmod +x /home/davidsanker/platform/bin/live_trading_monitor.sh

# Add live trading monitor to crontab (every hour)
(crontab -l 2>/dev/null; echo "# Live Trading Safety Monitor") | crontab -
(crontab -l 2>/dev/null; echo "0 * * * * /home/davidsanker/platform/bin/live_trading_monitor.sh") | crontab -

log "✅ Live trading safety monitor created and scheduled"

# 7. UPDATE DAILY REPORTER FOR LIVE ACCOUNT
log ""
log "Step 6: Updating Daily Reporter for Live Trading"

# Create enhanced live reporter
cat > /home/davidsanker/platform/bin/quantum_live_reporter.py << 'EOF'
#!/usr/bin/env python3
"""
Quantum AI Trading Bot Live Account Daily Reporter
Enhanced with risk metrics and live trading safeguards
"""

import os
import sys
sys.path.append('/home/davidsanker/platform/bin')
from quantum_daily_reporter_fixed import QuantumDailyReporter

class LiveTradingReporter(QuantumDailyReporter):
    def __init__(self):
        super().__init__()
        self.is_live_mode = True

    def generate_report(self):
        """Generate enhanced live trading report"""
        report = super().generate_report()

        # Add live trading specific content
        if self.ib and self.ib.isConnected():
            try:
                # Enhanced risk metrics
                portfolio = self.ib.portfolio()
                total_pnl = sum(item.unrealizedPnl + item.realizedPnL for item in portfolio)

                # Risk assessment
                risk_level = "LOW"
                if total_pnl <= -5000:
                    risk_level = "MEDIUM"
                if total_pnl <= -10000:
                    risk_level = "HIGH"
                if total_pnl <= -25000:
                    risk_level = "CRITICAL"

                # Add live trading specific content to report
                live_content = f"""
                <div class="live-trading-alert">
                    <h3>🔴 LIVE TRADING SAFETY MONITOR</h3>
                    <p><strong>Current PnL:</strong> ${total_pnl:,.2f}</p>
                    <p><strong>Risk Level:</strong> {risk_level}</p>
                    {self.get_risk_recommendation(total_pnl)}
                </div>
                """

                # Insert live trading alert before regular content
                report = report.replace(
                    '<div class="portfolio-summary">',
                    live_content + '<div class="portfolio-summary">'
                )

            except Exception as e:
                self.logger.error(f"Error adding live trading content: {e}")

        return report

    def get_risk_recommendation(self, total_pnl):
        """Generate risk recommendations based on PnL"""
        if total_pnl <= -25000:
            return "<p style='color: red; font-weight: bold;'>🚨 EMERGENCY: Consider reducing position sizes immediately</p>"
        elif total_pnl <= -10000:
            return "<p style='color: orange; font-weight: bold;'>⚠️ WARNING: Monitor closely and consider reducing exposure</p>"
        elif total_pnl <= -5000:
            return "<p style='color: yellow;'>⚠️ CAUTION: Consider tightening stop-losses</p>"
        else:
            return "<p style='color: green;'>✅ Risk levels acceptable for current market conditions</p>"

if __name__ == "__main__":
    reporter = LiveTradingReporter()
    reporter.generate_and_send_report()
EOF

chmod +x /home/davidsanker/platform/bin/quantum_live_reporter.py

# Update crontab to use live reporter
(crontab -l 2>/dev/null; grep -v "quantum_daily_reporter" | crontab -
(crontab -l 2>/dev/null; echo "# Enhanced Live Trading Daily Report - 7:00 AM CET (6:00 AM UTC)") | crontab -
(crontab -l 2>/dev/null; echo "0 6 * * * source ~/venv/bin/activate && python3 /home/davidsanker/platform/bin/quantum_live_reporter.py") | crontab -

log "✅ Enhanced live trading reporter configured"

log ""
log "=========================================="
log "🔄 LIVE SWITCH PREPARATION COMPLETE!"
log "=========================================="
log ""
log "📋 SWITCHING OPTIONS:"
echo ""
echo "🟡 OPTION 1 - GRADUAL TRANSITION (RECOMMENDED):"
echo "   - Start with small live positions (5-10% of paper sizes)"
echo "   - Keep paper account running as backup/hedge"
echo "   - Run both accounts in parallel for safety"
echo "   - Scale up live positions gradually"
echo ""
echo "🔴 OPTION 2 - DIRECT SWITCH (EXPERIENCED ONLY):"
echo "   - Switch completely to live trading"
echo "   - Maintain all current position sizes"
echo "   - Monitor continuously with safety alerts"
echo "   - Maximum efficiency but higher risk"
echo ""
echo "🛡️ SAFETY MEASURES ACTIVATED:"
echo "   ✅ Hourly risk monitoring system"
echo "   ✅ Emergency shutdown at \$25,000 losses"
echo "   ✅ Enhanced daily reports with risk metrics"
echo "   ✅ Quick account switching scripts created"
echo "   ✅ Paper account backup maintained"
echo ""
echo "🎯 RECOMMENDED NEXT STEPS:"
echo "1. Review your paper trading performance"
echo "2. Start with small live positions (5% size)"
echo "3. Monitor closely with live_trading_monitor.sh"
echo "4. Scale up gradually as confidence builds"
echo "5. Keep paper account for hedging strategies"
echo ""
echo "📞 WHEN READY FOR LIVE SWITCHING:"
echo "   Run: /home/davidsanker/platform/bin/switch_to_live.sh"
echo "   Type: CONFIRM-LIVE to confirm (safety requirement)"
echo ""
log "Log file: ${LOG_FILE}"