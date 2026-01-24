#!/bin/bash
# Test: System resources within limits

echo "Test 3: Resource Budget"
echo "================================="

PASS=true

# Check memory usage (should be < 90%)
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
if [ ${MEM_USAGE} -lt 90 ]; then
    echo "✓ Memory usage OK (${MEM_USAGE}%)"
else
    echo "✗ FAIL: Memory usage high (${MEM_USAGE}%)"
    PASS=false
fi

# Check disk usage (should be < 80%)
ROOT_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
DATA_USAGE=$(df -h /mnt/investor | awk 'NR==2 {print $5}' | sed 's/%//')

if [ ${ROOT_USAGE} -lt 80 ] && [ ${DATA_USAGE} -lt 80 ]; then
    echo "✓ Disk usage OK (Root: ${ROOT_USAGE}%, Data: ${DATA_USAGE}%)"
else
    echo "✗ FAIL: Disk usage high (Root: ${ROOT_USAGE}%, Data: ${DATA_USAGE}%)"
    PASS=false
fi

# Check CPU load (5-minute average should be < 2.0 on 2-core system)
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $2}' | sed 's/,//')
if (( $(echo "${CPU_LOAD} < 2.0" | bc -l) )); then
    echo "✓ CPU load OK (${CPU_LOAD})"
else
    echo "⚠ WARNING: CPU load high (${CPU_LOAD})"
fi

if [ "${PASS}" == "true" ]; then
    echo "================================="
    echo "Test 3: PASSED"
else
    echo "================================="
    echo "Test 3: FAILED"
    exit 1
fi
