#!/usr/bin/env sh
set -eu

: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=koreanlearn}"
: "${POSTGRES_USER:=korean}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$BACKUP_DIR/${POSTGRES_DB}_${timestamp}.dump"

pg_dump \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --format custom \
  --file "$file" \
  "$POSTGRES_DB"

find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.dump" -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete
echo "$file"
