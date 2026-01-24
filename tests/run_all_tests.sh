#!/bin/bash
# Master test runner

echo "========================================"
echo "ACCEPTANCE TESTS - PRODUCTION PLATFORM"
echo "========================================"
echo ""

FAILED=0

# Test 1: IB Gateway API
echo "Running Test 1: IB Gateway API..."
if bash ~/platform/tests/test_gateway_api.sh; then
    echo ""
else
    FAILED=$((FAILED + 1))
    echo ""
fi

# Test 2: Security
echo "Running Test 2: Security Checks..."
if bash ~/platform/tests/test_security.sh; then
    echo ""
else
    FAILED=$((FAILED + 1))
    echo ""
fi

# Test 3: Resources
echo "Running Test 3: Resource Budget..."
if bash ~/platform/tests/test_resources.sh; then
    echo ""
else
    FAILED=$((FAILED + 1))
    echo ""
fi

echo "========================================"
if [ ${FAILED} -eq 0 ]; then
    echo "ALL TESTS PASSED (3/3)"
    echo "========================================"
    exit 0
else
    echo "TESTS FAILED: ${FAILED}/3"
    echo "========================================"
    exit 1
fi
