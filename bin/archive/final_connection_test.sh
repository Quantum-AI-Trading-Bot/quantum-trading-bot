#!/bin/bash
echo "🧪 Final IB Gateway Connection Test"
echo "=================================="

echo "Step 1: Checking if Gateway is listening..."
if netstat -tlnp | grep -q 4002; then
    echo "✅ Port 4002 is listening"
else
    echo "❌ Port 4002 not found - Gateway may need restart"
    exit 1
fi

echo "Step 2: Testing Python API connection..."
source ~/venv/bin/activate

timeout 15 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=10)
    accounts = ib.managedAccounts()
    print(f'🎉 SUCCESS! Connected to account(s): {accounts}')

    # Test a basic operation
    time_req = ib.reqCurrentTime()
    print(f'📊 Server time: {time_req}')

    ib.disconnect()
    print('✅ Connection test completed successfully')
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎯 NEXT STEPS:"
    echo "1. Start your Quantum trading bot:"
    echo "   cd /home/davidsanker/investor_bot_migration_20251017_163810/investor"
    echo "   source ~/venv/bin/activate"
    echo "   python quantum_enhanced_trading_bot.py"
    echo ""
    echo "2. Your connection monitor should now work perfectly"
    echo "3. The chronic disconnects should be resolved"
else
    echo ""
    echo "⚠️  API TEST FAILED"
    echo "Please ensure:"
    echo "1. You're fully logged into IB Gateway in VNC"
    echo "2. API settings are enabled (see instructions above)"
    echo "3. No warning dialogs are blocking the interface"
fi