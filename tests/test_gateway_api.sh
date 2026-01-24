#!/bin/bash
# Test: IB Gateway API on port 4002 accepts connections

echo "Test 1: IB Gateway API Readiness"
echo "================================="

# Check port is listening
if nc -z 127.0.0.1 4002; then
    echo "✓ Port 4002 is listening"
else
    echo "✗ FAIL: Port 4002 not listening"
    exit 1
fi

# Test API connectivity
if timeout 10 python3 -c "
from ib_insync import IB
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=995)
    print('✓ API connection successful')
    ib.disconnect()
    exit(0)
except Exception as e:
    print(f'✗ FAIL: API connection failed: {e}')
    exit(1)
"; then
    echo "✓ API connectivity test PASSED"
else
    echo "✗ FAIL: API connectivity test FAILED"
    exit 1
fi

echo "================================="
echo "Test 1: PASSED"
