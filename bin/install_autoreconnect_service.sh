#!/bin/bash
#
# Installation script for Quantum Trading Bot Auto-Reconnect Service
# This script sets up the systemd service for automatic reconnection
#
# Author: David Sanker
# Date: January 28, 2026
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="quantum-trading-bot-autoreconnect"
SERVICE_FILE="${PLATFORM_DIR}/systemd/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "==========================================="
echo "Quantum Trading Bot Auto-Reconnect Setup"
echo "==========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

echo "✅ Found service file: $SERVICE_FILE"
echo ""

# Stop existing service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "🛑 Stopping existing service..."
    systemctl stop "$SERVICE_NAME"
fi

# Disable existing service if enabled
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "📴 Disabling existing service..."
    systemctl disable "$SERVICE_NAME"
fi

# Copy service file
echo "📝 Installing service file..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/${SERVICE_NAME}.service"
chmod 644 "$SYSTEMD_DIR/${SERVICE_NAME}.service"

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
systemctl enable "$SERVICE_NAME"

echo ""
echo "==========================================="
echo "✅ Installation Complete!"
echo "==========================================="
echo ""
echo "Service Management Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Log Files:"
echo "  Main:    /home/davidsanker/platform/logs/quantum-bot-service.log"
echo "  Errors:  /home/davidsanker/platform/logs/quantum-bot-service-error.log"
echo "  Trading: /home/davidsanker/platform/logs/quantum-trading-bot.log"
echo ""
echo "Health Check:"
echo "  python3 ${PLATFORM_DIR}/bin/check_connection_health.py"
echo ""
echo "To start the service now, run:"
echo "  sudo systemctl start $SERVICE_NAME"
echo ""
