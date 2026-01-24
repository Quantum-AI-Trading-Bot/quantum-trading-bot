#!/bin/bash

LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/monitor_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

# Check IB Gateway status
check_gateway_status() {
    if pgrep -f "java.*ibgateway" > /dev/null; then
        # Check API connectivity
        if timeout 10 python3 -c "
from ib_insync import IB
try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)
    print('OK')
    ib.disconnect()
except:
    print('AUTH_NEEDED')
" 2>/dev/null | grep -q "OK"; then
            echo "HEALTHY"
        else
            echo "NEEDS_AUTH"
        fi
    else
        echo "DOWN"
    fi
}

# Get current status
STATUS=$(check_gateway_status)

case "$STATUS" in
    "HEALTHY")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ IB Gateway is healthy and authenticated" >> "${LOG_FILE}"
        ;;
    "NEEDS_AUTH")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ IB Gateway needs authentication" >> "${LOG_FILE}"
        # Create alert
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🚨 ALERT: IB Gateway requires manual authentication" >> "${LOG_DIR}/alerts.log"
        echo "Please access VNC (localhost:5901) and complete login" >> "${LOG_DIR}/alerts.log"
        ;;
    "DOWN")
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ IB Gateway is down - attempting restart" >> "${LOG_FILE}"
        # Try to restart
        /home/davidsanker/platform/bin/complete_community_solution.sh
        ;;
esac
