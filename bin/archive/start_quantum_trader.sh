#!/bin/bash

echo "🚀 Starting Quantim AI Trading Bot..."
echo "==================================="

# Activate virtual environment
source ~/venv/bin/activate

# Check if Gateway API is ready
echo "📡 Checking IB Gateway API connection..."
if timeout 5 bash -c "echo '' | nc 127.0.0.1 4002" > /dev/null 2>&1; then
    echo "✅ Gateway API is ready!"
else
    echo "❌ Gateway API not responding - please complete login via VNC first"
    echo "   VNC: vncviewer 35.232.64.211:5901"
    exit 1
fi

# Start the Quantum Trading Bot
echo "🤖 Starting Quantum Enhanced Trading Bot..."
cd /home/davidsanker

# Run with timeout to prevent hanging
timeout 300 python quantum_trading_ml_package/quantum_trading/quantum_enhanced_trading_bot.py &

BOT_PID=$!
echo "📊 Trading Bot started with PID: $BOT_PID"

# Wait a moment and check if it's still running
sleep 5
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Quantum Trading Bot is running successfully!"
    echo "🎯 The bot is now connecting to IB Gateway and will start trading"
    echo ""
    echo "📈 Bot Features:"
    echo "   • 6-Phase Quantum Enhancement Stack"
    echo "   • LSTM Forecasting with Quantum Circuit Integration"
    echo "   • Reinforcement Learning Strategies"
    echo "   • Real-time Market Analysis"
    echo "   • Automated Trade Execution"
    echo ""
    echo "🔍 Monitor the bot:"
    echo "   tail -f /home/davidsanker/logs/trading_bot.log"
    echo ""
    echo "⚠️  To stop the bot: kill $BOT_PID"
else
    echo "❌ Trading bot failed to start - check logs for errors"
    exit 1
fi