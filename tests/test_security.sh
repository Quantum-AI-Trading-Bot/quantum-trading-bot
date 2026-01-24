#!/bin/bash
# Test: File permissions and network security

echo "Test 2: Security Checks"
echo "================================="

PASS=true

# Check config.ini permissions (should be 0600)
if [ "$(stat -c %a ~/IBC/config.ini)" == "600" ]; then
    echo "✓ config.ini has correct permissions (0600)"
else
    echo "✗ FAIL: config.ini has incorrect permissions"
    PASS=false
fi

# Check TrustedIPs setting
if grep -q "TrustedIPs=127.0.0.1" ~/IBGateway/jts.ini; then
    echo "✓ TrustedIPs correctly set to 127.0.0.1"
else
    echo "✗ FAIL: TrustedIPs not set or incorrect"
    PASS=false
fi

# Check port 4002 not exposed externally (should only listen on 127.0.0.1 or ::1)
if netstat -tuln | grep ":4002" | grep -qE "(127.0.0.1|::1)"; then
    echo "✓ Port 4002 listening on localhost only"
else
    echo "⚠ WARNING: Port 4002 may be exposed externally"
fi

# Check services run as davidsanker user
GATEWAY_USER=$(systemctl show -p User ib-gateway.service 2>/dev/null | cut -d= -f2)
BOT_USER=$(systemctl show -p User trading-bot.service 2>/dev/null | cut -d= -f2)

if [ "${GATEWAY_USER}" == "davidsanker" ] && [ "${BOT_USER}" == "davidsanker" ]; then
    echo "✓ Services run as davidsanker user"
elif [ -z "${GATEWAY_USER}" ]; then
    echo "⚠ Services not yet installed"
else
    echo "✗ FAIL: Services not running as davidsanker"
    PASS=false
fi

if [ "${PASS}" == "true" ]; then
    echo "================================="
    echo "Test 2: PASSED"
else
    echo "================================="
    echo "Test 2: FAILED"
    exit 1
fi
