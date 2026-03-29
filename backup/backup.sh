#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

HOURLY_DIR="${BACKUP_DIR}/hourly"
DAILY_DIR="${BACKUP_DIR}/daily"
DUMP_FILE="${HOURLY_DIR}/dump-$(date +%Y%m%d-%H%M).rdb"

mkdir -p "$HOURLY_DIR" "$DAILY_DIR"

# ── Take a consistent RDB snapshot ──────────────────────────────────
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb "$DUMP_FILE"

# Record success timestamp in Redis
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SET "backup:last_success" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup written to $DUMP_FILE"

# ── Daily: copy the first hourly snapshot of each day ───────────────
TODAY="$(date +%Y%m%d)"
DAILY_FILE="${DAILY_DIR}/dump-${TODAY}.rdb"
if [ ! -f "$DAILY_FILE" ]; then
  cp "$DUMP_FILE" "$DAILY_FILE"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) daily snapshot created: $DAILY_FILE"
fi

# ── Retention ───────────────────────────────────────────────────────
# Hourly: keep 2 days
find "$HOURLY_DIR" -name "*.rdb" -mtime +2 -delete

# Daily: keep 30 days
find "$DAILY_DIR" -name "*.rdb" -mtime +30 -delete
