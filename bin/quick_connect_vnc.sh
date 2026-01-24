#!/bin/bash
#
# Quick VNC Connection Script for IB Gateway Authentication
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🖥️  QUICK VNC CONNECTION WIZARD${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check if running as correct user
if [ "$(whoami)" != "davidsanker" ]; then
    echo -e "${RED}❌ Please run as davidsanker user${NC}"
    exit 1
fi

# Function to check VNC server
check_vnc_server() {
    if pgrep -f "tightvnc.*:1\|Xvnc.*:1" > /dev/null; then
        echo -e "${GREEN}✅ VNC server is running on display :1${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  VNC server not running${NC}"
        return 1
    fi
}

# Function to check IB Gateway
check_ib_gateway() {
    if pgrep -f "ibgateway" > /dev/null; then
        echo -e "${GREEN}✅ IB Gateway is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  IB Gateway not running${NC}"
        return 1
    fi
}

# Function to start VNC server
start_vnc_server() {
    echo -e "${BLUE}🚀 Starting VNC server...${NC}"

    # Kill existing sessions
    vncserver -kill :1 2>/dev/null || true
    sleep 2

    # Start new VNC server
    vncserver :1 -geometry 1920x1080 -depth 24

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ VNC server started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start VNC server${NC}"
        exit 1
    fi
}

# Function to start IB Gateway
start_ib_gateway() {
    echo -e "${BLUE}🚀 Starting IB Gateway...${NC}"
    /home/davidsanker/platform/bin/simple_permanent_gateway.sh start

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ IB Gateway started${NC}"
    else
        echo -e "${RED}❌ Failed to start IB Gateway${NC}"
    fi
}

# Main connection flow
main() {
    echo -e "${BLUE}🔍 Checking system status...${NC}"
    echo ""

    # Check VNC server
    if ! check_vnc_server; then
        echo -e "${YELLOW}Starting VNC server...${NC}"
        start_vnc_server
        sleep 3
    fi

    echo ""

    # Check IB Gateway
    if ! check_ib_gateway; then
        echo -e "${YELLOW}Starting IB Gateway...${NC}"
        start_ib_gateway
        sleep 5
    fi

    echo ""
    echo -e "${GREEN}🎉 SYSTEMS READY FOR CONNECTION${NC}"
    echo ""
    echo -e "${BLUE}📱 CONNECTION INSTRUCTIONS:${NC}"
    echo -e "${GREEN}1. Connect to VNC:${NC}"
    echo -e "   Command: ${YELLOW}vncviewer localhost:5901${NC}"
    echo -e "   Or use your VNC client with: ${YELLOW}localhost:5901${NC}"
    echo ""
    echo -e "${GREEN}2. Login to IB Gateway:${NC}"
    echo -e "   Username: ${YELLOW}amakua444${NC}"
    echo -e "   Password: ${YELLOW}[Your IB Password]${NC}"
    echo ""
    echo -e "${GREEN}3. Complete 2FA:${NC}"
    echo -e "   Use IBKR Mobile app to approve login"
    echo ""
    echo -e "${GREEN}4. Verify QUANTUM Bot:${NC}"
    echo -e "   Command: ${YELLOW}/home/davidsanker/platform/bin/start_quantum_trading_bot.sh status${NC}"
    echo ""

    # Quick connection attempt
    echo -e "${BLUE}🚀 Would you like to connect now? (y/n)${NC}"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔗 Attempting to launch VNC viewer...${NC}"

        if command -v vncviewer >/dev/null 2>&1; then
            vncviewer localhost:5901 &
        elif command -v xtightvncviewer >/dev/null 2>&1; then
            xtightvncviewer localhost:5901 &
        else
            echo -e "${YELLOW}⚠️  VNC viewer not found. Please install one:${NC}"
            echo -e "${YELLOW}   sudo apt-get install tigervnc-viewer${NC}"
            echo -e "${BLUE}   Then run: vncviewer localhost:5901${NC}"
        fi
    fi

    echo ""
    echo -e "${GREEN}✨ All systems are ready!${NC}"
    echo -e "${GREEN}   VNC Server: localhost:5901${NC}"
    echo -e "${GREEN}   IB Gateway: Running${NC}"
    echo -e "${GREEN}   QUANTUM Bot: Waiting for authentication${NC}"
}

# Run main function
main "$@"