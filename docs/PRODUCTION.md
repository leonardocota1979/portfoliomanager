# Produção (padrão profissional)

Este guia cobre **deploy profissional** e **boas práticas mínimas**.

## Checklist obrigatório
1. `SECRET_KEY` definido (não usar padrão de desenvolvimento).
2. `DATABASE_URL` apontando para banco persistente (Postgres recomendado).
3. HTTPS ativo (Render já fornece).
4. Backup automático do banco.
5. Logs acessíveis (Render ou VPS).
6. Dependências atualizadas (`pip install -r requirements.txt` no build).
7. Driver Postgres presente (`psycopg2-binary` em `requirements.txt`).

## Render — caminho rápido e profissional

### 1) Repositório
Suba o projeto no GitHub.

### 2) Criar Web Service
No Render:
- **New + → Web Service**
- Selecione o repositório
- O `render.yaml` será detectado automaticamente

### 3) Configurar variáveis obrigatórias
No painel do serviço, adicione:
- `SECRET_KEY` (obrigatório)
- `FINNHUB_KEY`
- `ALPHAVANTAGE_KEY`
- `ADMIN_BOOTSTRAP_USER`
- `ADMIN_BOOTSTRAP_PASS`
- `ADMIN_BOOTSTRAP_EMAIL`

### 4) Banco de dados
**Rápido (SQLite em disco)**  
Já configurado em `render.yaml` com disco persistente:
```
sqlite:////var/data/portfoliomanager.db
```

**Profissional (Postgres)**  
Crie um Postgres no Render e **substitua** `DATABASE_URL` no painel do serviço.

> Nota: se você definir `DATABASE_URL` no painel do Render, ele sobrescreve o valor do `render.yaml`.

Formato recomendado:
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

Compatibilidade:
- Se o provedor entregar `postgres://...`, o sistema normaliza automaticamente para `postgresql://...` via `app/core/settings.py`.

### 4.1) Seed automático de classes globais
No primeiro boot, o sistema cria classes globais padrão automaticamente
(Stocks, Bonds, REITs, Crypto, Commodities, Reserva de Valor).

## Desenvolvimento local x Produção (recomendado)
- **Local**: SQLite (rápido e simples).
- **Produção**: Postgres (persistência real).
- **Paridade total local**: opcionalmente use o **External Database URL** do Render no `.env`
  para testar localmente usando o mesmo Postgres.

## Estratégia econômica (Postgres Free + backup local)
Para reduzir custo, você pode usar **Postgres Free** e fazer backup diário local.
Quando o banco expirar, restaure o backup.

### Backup diário (local)
Requisito: `pg_dump` instalado (Homebrew: `brew install postgresql`).

```bash
export PG_BACKUP_URL="postgresql://user:pass@host:5432/db"
./scripts/maintenance/backup_postgres.sh
```

### Restaurar
```bash
export PG_BACKUP_URL="postgresql://user:pass@host:5432/db"
./scripts/maintenance/restore_postgres.sh var/backups/postgres/portfoliomanager_YYYYMMDD_HHMMSS.dump
```

### 5) Deploy
Finalize o deploy e acesse a URL pública fornecida pelo Render.

## Migrar para outro provedor Postgres (futuro)
1. Crie o novo Postgres no provedor final.
2. Faça backup do banco atual:
   ```bash
   export PG_BACKUP_URL="postgresql://user:pass@host:5432/db"
   ./scripts/maintenance/backup_postgres.sh
   ```
3. Restaure no novo Postgres:
   ```bash
   export PG_BACKUP_URL="postgresql://user:pass@novo-host:5432/novo-db"
   ./scripts/maintenance/restore_postgres.sh var/backups/postgres/portfoliomanager_YYYYMMDD_HHMMSS.dump
   ```
4. Atualize `DATABASE_URL` no ambiente de produção.
5. Faça deploy.

## VPS (IP fixo)
Para produção com controle total:
1. Criar VPS (Ubuntu)
2. Instalar Python + Nginx
3. Rodar Uvicorn via systemd
4. Configurar HTTPS (Let’s Encrypt)

## Arquivos relevantes
- `render.yaml`
- `.env.example`
- `docs/OPERATIONS.md`
