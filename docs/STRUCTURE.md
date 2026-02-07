# Estrutura e Padrões de Diretórios

Este documento define o padrão estrutural atual do projeto e o que pode ou não ser limpo.

## Raiz do projeto
- `app/`: aplicação FastAPI (routers, services, templates).
- `static/`: CSS e JS estáticos.
- `scripts/`: automações de setup/dev/manutenção.
- `docs/`: documentação funcional, técnica e operacional.
- `data/`: banco SQLite local (`portfoliomanager.db`).
- `var/`: runtime, logs e backups locais.

## Convenções de dados e runtime
- `var/.run/`: arquivos transitórios de execução (`*.pid`, `*.port`, `*.log`).
- `var/logs/`: logs de OCR/import e artefatos temporários de upload.
- `var/backups/postgres/`: dumps `.dump` de backup Postgres.

## Estrutura interna de `app/`
- `app/core/`: configuração única (`settings`) e paths da aplicação.
- `app/application/`: casos de uso para reduzir lógica direta em routers.
- `app/routers/`: camada HTTP (entrada/saída, validação de request/response).
- `app/services/`: integrações externas (preços, OCR).
- `app/database.py`: models SQLAlchemy e sessão.

## O que é temporário (limpeza permitida)
- `__pycache__/`, `*.pyc`, `*.pyo`.
- arquivos de runtime em `var/.run/`.
- uploads temporários em `var/logs/uploads/`.
- arquivos de cache OCR em `var/logs/ocr/*.txt`.
- arquivos de log conforme política operacional.

## O que não deve ser limpo automaticamente
- código-fonte (`app/`, `scripts/`, `docs/`, `static/`).
- banco local em `data/`.
- metadados de controle de versão (`.git/`).
- ambiente virtual (`venv/`), salvo ação explícita manual.

## Ferramenta oficial de limpeza
Script:
```bash
./scripts/maintenance/housekeeping.sh
```

Comportamento padrão:
- roda em `dry-run` (simulação).
- exige `--apply` para remoção real.
