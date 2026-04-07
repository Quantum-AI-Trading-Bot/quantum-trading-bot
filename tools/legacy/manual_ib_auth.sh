##############################################################################
# DEPRECATED - DO NOT USE
##############################################################################
# This script has been quarantined due to security concerns.
# It may contain hardcoded credentials or use unsafe automation practices.
# 
# Migration path:
# - Use VNC/noVNC for manual IB Gateway login
# - Use IBC (Interactive Brokers Controller) for automated startup
# - Monitor IB Gateway health via watchdog_ib_gateway.sh
#
# Manual login via VNC:
#   vncviewer 35.232.64.211:5901
#   or http://35.232.64.211:6080/vnc.html
##############################################################################

#!/bin/bash
set -euo pipefail

# ============================================================================
# Manual IB Gateway Authentication Helper
# Provides VNC connection info and manual steps
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "IB GATEWAY MANUAL AUTHENTICATION HELPER"
log "=========================================="

log ""
log "Your IB Gateway needs manual authentication."
log "This is a security requirement from Interactive Brokers."
log ""

# Check VNC status
log "1. VNC Connection Setup:"
if pgrep -x x11vnc > /dev/null; then
    log "   ✅ VNC server is running"
    log "   🖥️  Connect using: vnc://localhost:5901"
    log "   🔐 Password: (your VNC password)"
else
    log "   ❌ VNC server not running"
    log "   Start it with: sudo systemctl start x11vnc.service"
fi

log ""
log "2. Manual Authentication Steps:"
log "   1. Connect via VNC to see the IB Gateway screen"
log "   2. You should see the login dialog (if not logged in)"
log "   3. Complete the 2FA process using your mobile app"
log "   4. Wait for 'Active trading enabled' message"
log "   5. Look for 'API connections accepted' message"

log ""
log "3. Verify API Status:"
log "   After authentication, check:"
log "   - Gateway shows 'API connection settings: Configure > Enable'"
log "   - Port 4002 should be listening"
log "   - No error messages about API connections"

log ""
log "4. Quick Test Commands:"
log "   Test port: nc -z 127.0.0.1 4002 && echo 'Port OK' || echo 'Port FAIL'"
log "   Test API: source ~/venv/bin/activate && python3 -c \"from ib_insync import IB; ib=IB(); ib.connect('127.0.0.1',4002,clientId=999); print('API OK'); ib.disconnect()\""

log ""
log "5. Automation Issues:"
log "   IB requires manual authentication at least once per 24 hours."
log "   This cannot be fully automated due to security requirements."
log "   The IBC script helps but still needs initial manual login."

log ""
log "6. Alternative Solutions:"
log "   a) Use TWS (Trader Workstation) instead of Gateway"
log "   b) Set up a dedicated machine for stable connection"
log "   c) Consider running during market hours only"
log "   d) Use IB's cloud-based solutions for production"

log ""
log "=========================================="
log "After completing manual authentication:"
log "Run: /home/davidsanker/platform/bin/test_api_connection.sh"
log "=========================================="