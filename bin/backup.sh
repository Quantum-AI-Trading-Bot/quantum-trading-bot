#!/bin/bash
set -euo pipefail

# ============================================================================
# Automated Backup Script for Models and Configurations
# ============================================================================

BACKUP_ROOT="/mnt/investor/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "Starting backup: ${TIMESTAMP}"
log "=========================================="

# 1. Backup quantum models
log "[1/4] Backing up quantum models..."
MODEL_SRC="/home/davidsanker/brain-data/apps/investor/quantum_models"
if [[ -d "${MODEL_SRC}" ]]; then
    cp -r "${MODEL_SRC}" "${BACKUP_DIR}/quantum_models"
    log "   ✓ Models backed up ($(du -sh ${BACKUP_DIR}/quantum_models | cut -f1))"
else
    log "   ⚠ Model directory not found: ${MODEL_SRC}"
fi

# 2. Backup IBC configuration
log "[2/4] Backing up IBC config..."
cp ~/IBC/config.ini "${BACKUP_DIR}/config.ini"
chmod 600 "${BACKUP_DIR}/config.ini"
log "   ✓ IBC config backed up"

# 3. Backup Gateway configuration
log "[3/4] Backing up IB Gateway config..."
cp ~/IBGateway/jts.ini "${BACKUP_DIR}/jts.ini"
log "   ✓ Gateway config backed up"

# 4. Backup bot configuration
log "[4/4] Backing up bot config..."
if [[ -f ~/platform/config/bot_config.yaml ]]; then
    cp ~/platform/config/bot_config.yaml "${BACKUP_DIR}/bot_config.yaml"
    log "   ✓ Bot config backed up"
fi

# 5. Create tarball
log "Creating compressed archive..."
cd "${BACKUP_ROOT}"
tar -czf "${TIMESTAMP}.tar.gz" "${TIMESTAMP}"
rm -rf "${TIMESTAMP}"
log "   ✓ Archive created: ${BACKUP_ROOT}/${TIMESTAMP}.tar.gz"

# 6. Cleanup old backups (keep last 30 days)
log "Cleaning up old backups..."
find "${BACKUP_ROOT}" -name "*.tar.gz" -mtime +30 -delete
REMAINING=$(find "${BACKUP_ROOT}" -name "*.tar.gz" | wc -l)
log "   ✓ Cleanup complete (${REMAINING} backups remaining)"

log "=========================================="
log "Backup complete: ${BACKUP_ROOT}/${TIMESTAMP}.tar.gz"
log "=========================================="
