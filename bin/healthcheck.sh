#!/bin/bash
# Health check for trading bot service

# Check IB Gateway API
if ! nc -z 127.0.0.1 4002; then
    echo "ERROR: IB Gateway API not ready on port 4002"
    exit 1
fi

# Check virtual environment
if [ ! -d "/home/davidsanker/venv" ]; then
    echo "ERROR: Virtual environment missing"
    exit 1
fi

# Check trading bot code
if [ ! -f "/home/davidsanker/investor_bot_migration_20251017_163810/investor/trading_bot.py" ]; then
    echo "ERROR: Trading bot script missing"
    exit 1
fi

echo "✅ All health checks passed"
