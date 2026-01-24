#!/bin/bash
# reinstall_ib_gateway.sh - Reinstall IB Gateway from cached installer
# This script handles Gateway corruption by performing a clean reinstall

set -e

# Configuration
INSTALLER="/home/davidsanker/archives/installers/ibgateway-latest-standalone-linux-x64.sh"
GATEWAY_DIR="/home/davidsanker/IBGateway"
IBC_DIR="/home/davidsanker/IBC"
LOG_DIR="/home/davidsanker/platform/logs/ib-gateway"
BACKUP_DIR="/home/davidsanker/platform/logs/ib-gateway/backup_$(date +%Y%m%d_%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/reinstall.log"
}

error() {
    echo "${RED}ERROR: $1${NC}" >&2
    exit 1
}

success() {
    echo "${GREEN}✓ $1${NC}"
}

warning() {
    echo "${YELLOW}⚠ $1${NC}"
}

log "=== IB Gateway Reinstall Started ==="

# Check installer exists
if [ ! -f "$INSTALLER" ]; then
    error "Installer not found: $INSTALLER"
fi
success "Installer found"

# Stop all IB processes
log "Stopping all IB processes..."
pkill -f 'ibgateway|IBC' || true
sleep 5
success "Processes stopped"

# Backup existing installation
if [ -d "$GATEWAY_DIR" ]; then
    log "Backing up existing installation to $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$GATEWAY_DIR" "$BACKUP_DIR/"
    success "Backup created"
else
    warning "No existing Gateway installation found"
fi

# Remove corrupted installation
log "Removing corrupted Gateway installation..."
rm -rf "$GATEWAY_DIR"
success "Corrupted installation removed"

# Run installer
log "Running Gateway installer (unattended mode)..."
if ! "$INSTALLER" -q; then
    error "Installer failed"
fi
success "Gateway installed"

# Verify installation
log "Verifying installation..."
if [ ! -f "$GATEWAY_DIR/ibgateway.bin" ]; then
    error "Installation verification failed - ibgateway.bin not found"
fi
success "Installation verified"

log "=== IB Gateway Reinstall Complete ==="
success "IB Gateway successfully reinstalled"
echo ""
echo "Next steps:"
echo "  1. Start Gateway: $IBC_DIR/gatewaystart.sh"
echo "  2. Validate: /home/davidsanker/platform/bin/validate_ib_gateway.sh paper"
echo "  3. Enable watchdog: systemctl --user enable --now ibgateway-watchdog.service"
