#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PG_BACKUP_URL="postgresql://user:pass@host:5432/db" \
#   ./scripts/maintenance/backup_postgres.sh [output_dir]

OUT_DIR="${1:-var/backups/postgres}"
mkdir -p "$OUT_DIR"

if [[ -z "${PG_BACKUP_URL:-}" ]]; then
  echo "PG_BACKUP_URL não definido."
  echo "Exemplo: PG_BACKUP_URL=\"postgresql://user:pass@host:5432/db\""
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump não encontrado. Instale PostgreSQL client tools."
  exit 1
fi

ts="$(date +%Y%m%d_%H%M%S)"
file="$OUT_DIR/portfoliomanager_${ts}.dump"

echo "Backup -> $file"
pg_dump "$PG_BACKUP_URL" --format=custom --no-owner --no-privileges --file "$file"
echo "OK"
