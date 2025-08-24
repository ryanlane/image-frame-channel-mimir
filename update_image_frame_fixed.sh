#!/usr/bin/env bash
set -euo pipefail

# --- Update & build first ---
REPO="/home/ryan/code/image-frame-channel-mimir"

echo "Updating repo: ${REPO} ..."
git -C "${REPO}" fetch
git -C "${REPO}" pull

SRC="${HOME}/code/image-frame-channel-mimir/channels/photo_frame/"
DST="${HOME}/code/mimir-api/api-service/channels/photo_frame/"
UPLOADS_REL="assets/uploads/"
DATA_REL="data/"
UPLOADS_DST="${DST}${UPLOADS_REL}"
DATA_DST="${DST}${DATA_REL}"

# Ensure destination, uploads, and data dirs exist
mkdir -p "${DST}" "${UPLOADS_DST}" "${DATA_DST}"

# Does uploads contain any files?
if find "${UPLOADS_DST}" -type f -print -quit | grep -q .; then
  echo "Uploads folder is NOT empty — preserving existing uploads and data."
  # Sync everything except uploads and data; --delete applies to non-excluded paths only
  rsync -a --delete --exclude "${UPLOADS_REL}**" --exclude "${DATA_REL}**" "${SRC}" "${DST}"
else
  echo "Uploads folder is empty (or missing) — syncing uploads but preserving data."
  # Safe to include uploads on first sync but still preserve data
  rsync -a --delete --exclude "${DATA_REL}**" "${SRC}" "${DST}"
fi

echo "Synced: ${SRC} → ${DST}"
echo "Preserved: uploads and data directories with database and thumbnails"
