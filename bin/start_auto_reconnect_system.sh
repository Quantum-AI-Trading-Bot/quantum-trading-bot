#!/bin/bash
# start_auto_reconnect_system.sh - Start the complete auto-reconnect system
# This ensures your trading bot is ALWAYS online with 24/7 monitoring

set -e

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
mkdir -p "$LOG_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 STARTING 24/7 AUTO-RECONNECT SYSTEM"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Make scripts executable
echo "📋 Making scripts executable..."
chmod +x /home/davidsanker/platform/bin/auto_reconnect_watchdog.sh
chmod +x /home/davidsanker/IBC/gatewaystart.sh

# Step 2: Stop any existing watchdog
echo "🛑 Stopping any existing watchdog..."
pkill -f "auto_reconnect_watchdog.sh" || true
pkill -f "watchdog_ib_gateway.sh" || true
sleep 2

# Step 3: Update IBC config for better auto-reconnect
echo "⚙️  Updating IBC configuration..."
if grep -q "ForceTwsReconnect=no" /home/davidsanker/IBC/config.ini; then
    sed -i 's/ForceTwsReconnect=no/ForceTwsReconnect=yes/' /home/davidsanker/IBC/config.ini
    echo "✅ Updated ForceTwsReconnect=yes in IBC config"
else
    echo "✅ ForceTwsReconnect already enabled"
fi

# Step 4: Start the continuous watchdog
echo "🔄 Starting continuous auto-reconnect watchdog..."
nohup /home/davidsanker/platform/bin/auto_reconnect_watchdog.sh \
    > "$LOG_DIR/watchdog_output.log" 2>&1 &

WATCHDOG_PID=$!
echo "✅ Watchdog started (PID: $WATCHDOG_PID)"

# Step 5: Verify it's running
sleep 3
if pgrep -f "auto_reconnect_watchdog.sh" > /dev/null; then
    echo "✅ Watchdog is running and monitoring"
else
    echo "❌ Failed to start watchdog"
    exit 1
fi

# Step 6: Update crontab to remove conflicting jobs
echo "📅 Updating crontab to use continuous monitoring..."
# Comment out the old monitoring scripts
(crontab -l 2>/dev/null | grep -v "ib_gateway_monitor.sh" | grep -v "watchdog_ib_gateway.sh" | crontab -) || true

# Add new cron job to ensure watchdog starts on reboot
(crontab -l 2>/dev/null; echo "@reboot sleep 60 && /home/davidsanker/platform/bin/auto_reconnect_watchdog.sh > /dev/null 2>&1 &") | crontab -

echo "✅ Crontab updated"

# Step 7: Create systemd service (optional but recommended)
echo "🔧 Creating systemd service..."
cat > /tmp/auto-reconnect-watchdog.service << 'EOF'
[Unit]
Description=IB Gateway Auto-Reconnect Watchdog
After=network.target

[Service]
Type=simple
User=davidsanker
ExecStart=/home/davidsanker/platform/bin/auto_reconnect_watchdog.sh
Restart=always
RestartSec=10
StandardOutput=append:/home/davidsanker/platform/logs/ib-gateway/watchdog_systemd.log
StandardError=append:/home/davidsanker/platform/logs/ib-gateway/watchdog_systemd_error.log

[Install]
WantedBy=multi-user.target
EOF

# Copy to systemd directory
sudo cp /tmp/auto-reconnect-watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auto-reconnect-watchdog.service
echo "✅ Systemd service created and enabled"

# Step 8: Show status
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ AUTO-RECONNECT SYSTEM ACTIVATED"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📊 Monitoring Status:"
echo "  • Watchdog: Running (PID: $(pgrep -f 'auto_reconnect_watchdog.sh' | head -1))"
echo "  • Check Interval: Every 30 seconds"
echo "  • Log File: $LOG_DIR/auto_reconnect.log"
echo ""
echo "🛡️  Protection Layers:"
echo "  ✅ Continuous process monitoring (30s intervals)"
echo "  ✅ API port connectivity checks"
echo "  ✅ Trading bot process monitoring"
echo "  ✅ Automatic restart on failure"
echo "  ✅ Systemd supervision (auto-restart on crash)"
echo "  ✅ Boot-time activation"
echo ""
echo "📝 Commands:"
echo "  • Check logs: tail -f $LOG_DIR/auto_reconnect.log"
echo "  • Stop monitoring: pkill -f auto_reconnect_watchdog.sh"
echo "  • Start monitoring: /home/davidsanker/platform/bin/start_auto_reconnect_system.sh"
echo "  • Check status: ps aux | grep auto_reconnect_watchdog"
echo ""
echo "🎯 Your trading bot is now PROTECTED against disconnections!"
echo "═══════════════════════════════════════════════════════════════"
