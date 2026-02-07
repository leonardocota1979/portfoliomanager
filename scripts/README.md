# Scripts

Organização padrão de automações e utilitários do projeto.

## `setup/`
Scripts de bootstrap e correções iniciais de ambiente.

## `dev/`
Ferramentas de desenvolvimento (diagnóstico e utilitários locais).

## `maintenance/`
Manutenção operacional (migrações de suporte, usuários, backup/restore).

Arquivos principais:
- `scripts/maintenance/housekeeping.sh`: limpeza segura de temporários (dry-run por padrão).
- `scripts/maintenance/backup_postgres.sh`: backup de Postgres para `var/backups/postgres/`.
- `scripts/maintenance/restore_postgres.sh`: restore de dump Postgres.

## `migrations/`
Migrações pontuais em SQLite para compatibilidade retroativa.

## Regras de uso
- Execute sempre da raiz do projeto.
- Em produção, prefira migrações idempotentes e scripts sem efeitos destrutivos.
- Backups de Postgres devem sair em `var/backups/postgres/`.
