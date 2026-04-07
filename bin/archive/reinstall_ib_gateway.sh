#!/bin/bash
#
# IB Gateway Reinstall Script
# Repairs or replaces corrupted IB Gateway installation
#
# This script is idempotent and can be safely rerun.
#

set -e

GATEWAY_DIR="/home/davidsanker/IBGateway"
IBC_DIR="/home/davidsanker/IBC"
INSTALLER_DIR="/home/davidsanker/archives/installers"
ARCHIVE_DIR="/home/davidsanker/archives/ibgateway_backup"
LOG_DIR="/home/davidsanker/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "=========================================="
echo "🔧 IB Gateway Reinstall Script"
echo "=========================================="
echo ""

# Pre-flight check
log "Running pre-flight checks..."

# Step 1: Check for installer artifact
echo ""
echo "[1/8] Checking for installer artifact..."

mkdir -p "$INSTALLER_DIR"

INSTALLER=""
if [ -f "$INSTALLER_DIR/ibgateway-latest.sh" ]; then
    INSTALLER="$INSTALLER_DIR/ibgateway-latest.sh"
    success "Found installer: $INSTALLER"
elif [ -f "$INSTALLER_DIR/ibgateway-*.sh" ]; then
    INSTALLER=$(ls "$INSTALLER_DIR"/ibgateway-*.sh 2>/dev/null | head -1)
    success "Found installer: $INSTALLER"
else
    error "No IB Gateway installer found"
    echo ""
    echo "📋 ACTION REQUIRED:"
    echo "   1. Download IB Gateway for Linux from:"
    echo "      https://www.interactivebrokers.com/en/trading/ibgateway-standalone.php"
    echo ""
    echo "   2. Place the installer in: $INSTALLER_DIR"
    echo "      Recommended name: ibgateway-latest.sh"
    echo ""
    echo "   3. Make it executable: chmod +x $INSTALLER_DIR/ibgateway-latest.sh"
    echo ""
    echo "   4. Run this script again"
    exit 10
fi

# Verify installer is executable
if [ ! -x "$INSTALLER" ]; then
    warning "Installer is not executable, fixing..."
    chmod +x "$INSTALLER"
fi

# Step 2: Stop all services
echo ""
echo "[2/8] Stopping IB Gateway services..."

# Stop watchdog
if pgrep -f "watchdog_ib_gateway.sh" > /dev/null 2>&1; then
    log "Stopping watchdog..."
    pkill -f "watchdog_ib_gateway.sh" || true
    sleep 2
fi

# Stop IBC/Gateway processes
log "Stopping IB Gateway processes..."
pkill -9 -f "ibgateway" 2>/dev/null || true
pkill -9 -f "IbcGateway" 2>/dev/null || true
sleep 3

if pgrep -f "ibgateway" > /dev/null 2>&1; then
    warning "Some processes still running, waiting..."
    sleep 5
    pkill -9 -f "ibgateway" 2>/dev/null || true
fi

success "All services stopped"

# Step 3: Backup existing installation
echo ""
echo "[3/8] Backing up existing installation..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$ARCHIVE_DIR/$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

if [ -d "$GATEWAY_DIR" ]; then
    log "Backing up IB Gateway to: $BACKUP_DIR"
    cp -a "$GATEWAY_DIR" "$BACKUP_DIR/"
    success "Backup complete"
else
    warning "No existing IB Gateway installation to backup"
fi

# Also backup IBC config (NOT credentials, just the config)
if [ -f "$IBC_DIR/config.ini" ]; then
    log "Backing up IBC config..."
    cp "$IBC_DIR/config.ini" "$BACKUP_DIR/ibc_config.ini.backup"
    success "IBC config backed up"
fi

# Step 4: Remove corrupted installation
echo ""
echo "[4/8] Removing corrupted installation..."

if [ -d "$GATEWAY_DIR" ]; then
    log "Removing old IB Gateway directory..."
    rm -rf "$GATEWAY_DIR"
    success "Removed old installation"
fi

# Step 5: Run installer
echo ""
echo "[5/8] Running IB Gateway installer..."
echo "   This may take several minutes..."
echo ""

log "Starting installer: $INSTALLER"

# Run installer in unattended mode if possible
# Try --mode unattended flag first, if that fails run normally
if "$INSTALLER" --mode unattended 2>/dev/null; then
    success "Installer completed (unattended mode)"
else
    warning "Unattended mode not supported, running in normal mode..."
    info "You may need to complete installation steps in the GUI that appears"
    info "Press Ctrl+C to abort if needed"

    # Set DISPLAY for GUI
    export DISPLAY=:1

    # Run installer (will open in VNC if Xvfb running)
    "$INSTALLER" &
    INSTALLER_PID=$!

    log "Installer started with PID: $INSTALLER_PID"
    log "Waiting for installer to complete..."

    # Wait for installer process to finish
    # Check every 10 seconds
    for i in {1..60}; do
        if ! ps -p $INSTALLER_PID > /dev/null 2>&1; then
            log "Installer process completed"
            break
        fi
        echo -ne "\r   Waiting... ${i}/60 attempts ($((i*10)) seconds)"
        sleep 10
    done
    echo ""

    # Final check
    if ps -p $INSTALLER_PID > /dev/null 2>&1; then
        warning "Installer still running after 10 minutes"
        log "Continuing anyway (installation may be complete)"
    fi

    success "Installer step completed"
fi

# Step 6: Restore IBC config
echo ""
echo "[6/8] Restoring IBC configuration..."

# Check if IBC directory exists
if [ ! -d "$IBC_DIR" ]; then
    error "IBC directory not found: $IBC_DIR"
    error "Cannot restore configuration"
    exit 1
fi

# Check if backup exists
if [ -f "$BACKUP_DIR/ibc_config.ini.backup" ]; then
    log "Restoring IBC config from backup..."
    cp "$BACKUP_DIR/ibc_config.ini.backup" "$IBC_DIR/config.ini"
    success "IBC config restored"
else
    warning "No IBC config backup found"
    warning "You may need to configure IBC manually"
fi

# Step 7: Verify installation
echo ""
echo "[7/8] Verifying installation..."

REQUIRED_AFTER_INSTALL=(
    "$GATEWAY_DIR/ibgateway.bin"
    "$GATEWAY_DIR/jars"
    "$GATEWAY_DIR/.install4j/i4jruntime.jar"
)

MISSING_AFTER_INSTALL=0
for item in "${REQUIRED_AFTER_INSTALL[@]}"; do
    if ls "$item" 1>/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} Found: $item"
    else
        echo -e "  ${RED}❌${NC} Missing: $item"
        MISSING_AFTER_INSTALL=$((MISSING_AFTER_INSTALL + 1))
    fi
done

if [ $MISSING_AFTER_INSTALL -gt 0 ]; then
    error "Installation verification failed - missing files"
    exit 11
fi

# Check Java can run
if java -version >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Java functional"
else
    error "Java not working"
    exit 13
fi

success "Installation verification passed"

# Step 8: Final message
echo ""
echo "[8/8] Installation complete!"
echo ""
echo "=========================================="
echo -e "${GREEN}✅ REINSTALL SUCCESSFUL${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. If you see a login window in VNC:"
echo "   - Complete login with your IB credentials"
echo "   - Complete 2FA"
echo "   - Verify API is enabled: Configure → API → Settings"
echo "     ✅ Enable ActiveX/Socket Clients"
echo "     Socket Port: 4002"
echo "     ❌ Uncheck 'Read-Only API'"
echo ""
echo "2. After login, verify:"
echo "   ss -ltnp | grep 4002"
echo ""
echo "3. Run recovery script:"
echo "   /home/davidsanker/recover_ib_gateway.sh"
echo ""
echo "4. Run validator:"
echo "   cd /mnt/investor/projects/Investor"
echo "   ./validate_golden_path.sh paper"
echo ""
