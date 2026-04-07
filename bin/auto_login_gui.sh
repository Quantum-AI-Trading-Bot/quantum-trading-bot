#!/bin/bash
set -e

export DISPLAY=:1

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Find and activate IB Gateway window
WINDOW_ID=$(xdotool search --class "Gateway" | head -1)
if [ -z "$WINDOW_ID" ]; then
    log "❌ IB Gateway window not found"
    exit 1
fi

log "Found IB Gateway window: $WINDOW_ID"

# Bring window to front (multiple methods)
xdotool windowactivate "$WINDOW_ID" || true
xdotool windowraise "$WINDOW_ID" || true
sleep 2

# Clear any existing text and enter credentials
log "Entering credentials..."
xdotool key "Ctrl+a"  # Select all
sleep 0.5
xdotool type "amakua444"  # Username
sleep 0.5
xdotool key Tab
sleep 0.5
xdotool type "YOUR_IB_PASSWORD"  # Password
sleep 0.5
xdotool key Return

log "✅ Credentials entered - please complete 2FA on your mobile device"
