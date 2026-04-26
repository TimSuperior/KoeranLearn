#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Usage: restore_postgres.sh /backups/koreanlearn_YYYYMMDDTHHMMSSZ.dump" >&2
  exit 2
fi

: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=koreanlearn}"
: "${POSTGRES_USER:=korean}"

pg_restore \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean \
  --if-exists \
  "$1"
