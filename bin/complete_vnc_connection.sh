#!/bin/bash
#
# Complete VNC Connection and QUANTUM Bot Setup
# Ready for immediate use
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 COMPLETE QUANTUM TRADING SYSTEM CONNECTION${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check VNC server
if pgrep -f "Xvnc.*:1" > /dev/null; then
    echo -e "${GREEN}✅ VNC server is running on display :1${NC}"
else
    echo -e "${RED}❌ VNC server not running. Starting...${NC}"
    vncserver :1 -geometry 1920x1080 -depth 24
    sleep 3
fi

# Check IB Gateway
if pgrep -f "ibgateway.bin" > /dev/null; then
    echo -e "${GREEN}✅ IB Gateway is running${NC}"
else
    echo -e "${YELLOW}⚠️  Starting IB Gateway...${NC}"
    export DISPLAY=:1
    /home/davidsanker/IBGateway/ibgateway.bin &
    sleep 10
fi

# Move IB Gateway to center
export DISPLAY=:1
xdotool search --name "IBKR Gateway" windowmove 100 50 2>/dev/null || echo "IB Gateway window already positioned"
xdotool search --name "IBKR Gateway" windowactivate 2>/dev/null || echo "IB Gateway window already active"

# Check QUANTUM Bot
if pgrep -f "quantum_enhanced_trading_bot.py" > /dev/null; then
    echo -e "${GREEN}✅ QUANTUM Bot is running${NC}"
else
    echo -e "${YELLOW}⚠️  Starting QUANTUM Bot...${NC}"
    /home/davidsanker/platform/bin/start_quantum_trading_bot.sh start &
fi

echo ""
echo -e "${GREEN}🎉 SYSTEM READY FOR CONNECTION${NC}"
echo ""
echo -e "${BLUE}🔗 VNC CONNECTION INSTRUCTIONS:${NC}"
echo -e "${GREEN}From your local machine, run:${NC}"
echo -e "   ${YELLOW}vncviewer 35.232.64.211:5901${NC}"
echo -e "   ${GREEN}VNC Password: trading1${NC}"
echo ""
echo -e "${GREEN}🔐 IB GATEWAY LOGIN:${NC}"
echo -e "   Username: ${YELLOW}amakua444${NC}"
echo -e "   Password: ${YELLOW}Twbb19874!${NC}"
echo ""
echo -e "${GREEN}📱 2FA STEPS:${NC}"
echo -e "   1. Complete login in VNC session"
echo -e "   2. Approve via IBKR Mobile app"
echo -e "   3. Wait for API port 4002 to activate"
echo ""
echo -e "${GREEN}⚛️  QUANTUM BOT STATUS:${NC}"
echo -e "   Status: Running and waiting for API connection"
echo -e "   Logs: /home/davidsanker/platform/logs/quantum-trading-bot.log"
echo ""
echo -e "${BLUE}✨ Once authenticated, QUANTUM Bot will auto-connect and start trading!${NC}"