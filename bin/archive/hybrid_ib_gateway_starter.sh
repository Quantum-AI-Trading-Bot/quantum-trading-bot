#!/bin/bash
set -e

# Hybrid IB Gateway Starter - Manual Login + Automated Setup
echo "🚀 Hybrid IB Gateway Starter"
echo "============================="

LOG_FILE="/home/davidsanker/logs/ib_gateway_hybrid_start.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to start VNC server
start_vnc() {
    log "🖥️ Starting VNC server for GUI access..."

    # Kill existing VNC
    pkill -f "x11vnc" 2>/dev/null || true
    sleep 2

    # Start VNC server
    export DISPLAY=:1
    x11vnc -display :1 -forever -nopw -quiet -create -bg 2>/dev/null &

    sleep 3
    log "✅ VNC server started on localhost:5901"
}

# Function to start IB Gateway manually
start_ib_gateway() {
    log "📡 Starting IB Gateway..."

    # Kill existing processes
    pkill -f "java.*ibgateway" 2>/dev/null || true
    pkill -f "ibgateway" 2>/dev/null || true
    sleep 3

    # Start IB Gateway with GUI
    /home/davidsanker/IBGateway/ibgateway.bin &

    sleep 15
    log "✅ IB Gateway started"
}

# Function to wait for API port with guidance
wait_for_api_with_guidance() {
    log "⏳ Waiting for IB Gateway login and API setup..."
    log ""
    log "📋 MANUAL STEPS REQUIRED:"
    log "   1. Connect to VNC: vnc://localhost:5901"
    log "   2. Login with: amakua444 / YOUR_IB_PASSWORD"
    log "   3. Complete 2FA on your mobile device"
    log "   4. Go to Configure → API → Settings"
    log "   5. Enable: 'Enable ActiveX and Socket Clients'"
    log "   6. Set: 'Socket port' to 4002"
    log "   7. Disable: 'Read-Only API' (for trading)"
    log "   8. Add: '127.0.0.1' to trusted IPs"
    log "   9. Click OK and restart if prompted"
    log ""
    log "⏳ Waiting for API port 4002 to become ready..."

    # Wait up to 10 minutes with progress updates
    for i in {1..60}; do
        if timeout 3 bash -c "echo '' | nc 127.0.0.1 4002" 2>/dev/null; then
            log "✅ API port 4002 is ready!"
            return 0
        fi

        if [ $((i % 10)) -eq 0 ]; then
            elapsed=$((i * 10))
            log "⏳ Still waiting... (${elapsed}s elapsed) - Please complete the manual login steps above"
        fi

        sleep 10
    done

    log "❌ API port not ready after 10 minutes"
    return 1
}

# Function to test API connection
test_api_connection() {
    log "🔗 Testing API connection..."

    source /home/davidsanker/trading_bot_venv/bin/activate

    if python3 -c "
from ib_insync import IB
import sys
import time

ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=9999, timeout=30)
    print('✅ API connection successful!')
    server_time = ib.reqCurrentTime()
    print(f'✅ Server time: {server_time}')
    ib.disconnect()
    sys.exit(0)
except Exception as e:
    print(f'❌ API connection failed: {e}')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ API connection verified!"
        return 0
    else
        log "❌ API connection verification failed"
        return 1
    fi
}

# Function to start trading bot
start_trading_bot() {
    log "🤖 Starting Quantum Trading Bot..."

    cd /home/davidsanker/investor_bot_migration_20251017_163810/investor

    # Update client ID to avoid conflicts
    sed -i 's/IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "1003"))/IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "1004"))/' trading_bot.py

    # Start trading bot
    nohup python3 trading_bot.py >> "$LOG_FILE" 2>&1 &

    BOT_PID=$!
    log "✅ Trading bot started with PID: $BOT_PID"

    # Wait and verify
    sleep 10
    if kill -0 $BOT_PID 2>/dev/null; then
        log "✅ Trading bot is running successfully!"
        return 0
    else
        log "❌ Trading bot failed to start"
        return 1
    fi
}

# Main execution
main() {
    log "🎯 Starting hybrid IB Gateway and trading bot setup..."

    # Step 1: Start VNC server
    start_vnc

    # Step 2: Start IB Gateway
    start_ib_gateway

    # Step 3: Wait for manual login with guidance
    if wait_for_api_with_guidance; then
        # Step 4: Test API connection
        if test_api_connection; then
            # Step 5: Start trading bot
            if start_trading_bot; then
                log ""
                log "🎉 SUCCESS: Complete trading system is running!"
                log "=========================================="
                log "📊 Trading Bot: Active"
                log "🔗 IB Gateway API: Connected"
                log "🌐 VNC Access: localhost:5901"
                log "📋 Logs: $LOG_FILE"
                log ""
                log "Monitor with: tail -f $LOG_FILE"
                log "Stop bot with: pkill -f trading_bot.py"

                return 0
            else
                log "❌ Trading bot startup failed"
                return 1
            fi
        else
            log "❌ API connection failed"
            return 1
        fi
    else
        log "❌ IB Gateway setup not completed in time"
        return 1
    fi
}

# Handle interruption
trap 'log "⏹️ Process interrupted"; exit 1' INT TERM

# Run main function
main

# Show final status
if [ $? -eq 0 ]; then
    echo ""
    echo "🎊 SUCCESS: Trading system is fully operational!"
    echo "==============================================="
    echo "✅ IB Gateway: Running and configured"
    echo "✅ API Connection: Active on port 4002"
    echo "✅ Trading Bot: Running and ready to trade"
    echo "✅ VNC Access: Available at localhost:5901"
else
    echo ""
    echo "❌ SETUP INCOMPLETE"
    echo "=================="
    echo "🔧 Complete the manual steps in VNC (localhost:5901)"
    echo "📋 Check logs: $LOG_FILE"
    echo "🔄 Run again after completing manual setup"
fi