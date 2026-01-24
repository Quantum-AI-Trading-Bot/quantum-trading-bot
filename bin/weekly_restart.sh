#!/bin/bash
# Weekly system restart

LOG_FILE="/home/davidsanker/platform/logs/maintenance/weekly_$(date +%Y%m%d).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] Starting weekly restart..." >> "$LOG_FILE"

# Stop trading bot
sudo systemctl stop trading-bot.service
sleep 5

# Restart IB Gateway
pkill -f "java.*ibgateway" || true
sleep 10

# Start fresh system
/home/davidsanker/platform/bin/complete_trading_system_start.sh

# Start trading bot service
sudo systemctl start trading-bot.service

echo "[$(date)] Weekly restart completed" >> "$LOG_FILE"
