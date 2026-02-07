#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PG_BACKUP_URL="postgresql://user:pass@host:5432/db" \
#   ./scripts/maintenance/restore_postgres.sh backups/postgres/portfoliomanager_YYYYMMDD_HHMMSS.dump

if [[ -z "${PG_BACKUP_URL:-}" ]]; then
  echo "PG_BACKUP_URL não definido."
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_restore não encontrado. Instale PostgreSQL client tools."
  exit 1
fi

if [[ -z "${1:-}" ]]; then
  echo "Informe o arquivo .dump para restaurar."
  exit 1
fi

file="$1"
if [[ ! -f "$file" ]]; then
  echo "Arquivo não encontrado: $file"
  exit 1
fi

echo "Restore <- $file"
pg_restore --clean --if-exists --no-owner --no-privileges --dbname "$PG_BACKUP_URL" "$file"
echo "OK"
