#!/usr/bin/env bash
set -euo pipefail

# --- Update & build first ---
REPO="/home/ryan/code/image-frame-channel-mimir"

echo "Updating repo: ${REPO} ..."
git -C "${REPO}" fetch
git -C "${REPO}" pull

SRC="${HOME}/code/image-frame-channel-mimir/channels/photo_frame/"
DST="/var/opt/mimir/mimir-api/channels/photo_frame"
UPLOADS_REL="assets/uploads/"
DATA_REL="data/"
UPLOADS_DST="${DST}/${UPLOADS_REL}"
DATA_DST="${DST}/${DATA_REL}"

# Clean up any malformed directories from previous syncs
echo "Cleaning up malformed directories..."

# Ensure destination, uploads, and data dirs exist
sudo mkdir -p "${DST}" "${UPLOADS_DST}" "${DATA_DST}"

# Does uploads contain any files?
if find "${UPLOADS_DST}" -type f -print -quit | grep -q .; then
  echo "Uploads folder is NOT empty — preserving existing uploads and data."
  # Sync everything except uploads and data; --delete applies to non-excluded paths only
  # CRITICAL: Source has trailing slash to copy contents, destination does NOT to create target dir
  sudo rsync -a --delete --exclude "${UPLOADS_REL}" --exclude "${DATA_REL}" "${SRC}" "${DST}"
else
  echo "Uploads folder is empty (or missing) — syncing uploads but preserving data."
  # Safe to include uploads on first sync but still preserve data
  # CRITICAL: Source has trailing slash to copy contents, destination does NOT to create target dir
  sudo rsync -a --delete --exclude "${DATA_REL}" "${SRC}" "${DST}"
fi

echo "Synced: ${SRC} → ${DST}"

# --- CRITICAL: Fix ownership and permissions ---
echo "Setting correct ownership and permissions..."

# Set ownership to mimir-api user and group
sudo chown -R mimir-api:mimir-api "${DST}"

# Set appropriate permissions:
# - Directories: 755 (rwxr-xr-x) - owner can read/write/execute, others can read/execute
# - Files: 644 (rw-r--r--) - owner can read/write, others can read
sudo find "${DST}" -type d -exec chmod 755 {} \;
sudo find "${DST}" -type f -exec chmod 644 {} \;

# Ensure Python files are executable if needed
sudo find "${DST}" -name "*.py" -exec chmod 755 {} \;

# Special permissions for uploads directory - ensure it's writable by the service
sudo chmod 755 "${UPLOADS_DST}"
sudo chmod 755 "${DATA_DST}"

echo "✅ Ownership set to mimir-api:mimir-api"
echo "✅ Directory permissions set to 755"
echo "✅ File permissions set to 644"
echo "✅ Python files set to 755"
echo "Preserved: uploads and data directories with database and thumbnails"

# Restart the mimir-api service to pick up changes
echo "Restarting mimir-api service..."
sudo systemctl restart mimir-api

echo "✅ Service restarted. Channel should now load properly."