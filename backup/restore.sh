#!/usr/bin/env bash
set -euo pipefail

# NOTE: With Docker named volumes, you must know the volume mount path on the
# host or use "docker cp" to place the file into the redis container's /data
# directory. The approach below assumes you can write to the volume directly
# (e.g., via a bind mount or by running from a container that shares the volume).

if [ -z "${1:-}" ]; then
  echo "Usage: $0 /backups/daily/dump-20260329.rdb"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: file not found: $BACKUP_FILE"
  exit 1
fi

echo "Stopping redis service..."
docker compose stop redis

echo "Copying $BACKUP_FILE to redis data volume..."
cp "$BACKUP_FILE" /data/dump.rdb

echo "Starting redis service..."
docker compose start redis

echo "Restore complete."
