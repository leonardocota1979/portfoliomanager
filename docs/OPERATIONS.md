# Operações e Execução

## Requisitos
- Python 3.11+
- macOS (validado)

## Instalação
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Variáveis de ambiente
No `.env`:
- `DATABASE_URL` (SQLite por padrão; pode apontar para Postgres)
- `DB_SCHEMA` (schema do projeto no Postgres compartilhado)
- `ENFORCE_DB_SCHEMA` (falha startup se schema ativo divergir)
- `FINNHUB_KEY`
- `ALPHAVANTAGE_KEY`
- `OCR_LANG`
- `OCR_CMD`

Leitura centralizada:
- Todas as variáveis são carregadas por `app/core/settings.py`.
- Isso reduz inconsistência entre ambiente local e produção.

## Executar
Use o script:
```bash
./devctl.sh
```

## Deploy no Render (produção rápida)
1. Suba o projeto para um repositório Git (GitHub).
2. No Render, crie um **New Web Service** apontando para o repositório.
3. Use o arquivo `render.yaml` (deploy automático).

O Render irá:
- Criar o serviço web
- Instalar dependências
- Configurar o SQLite em disco persistente

Variáveis principais (já no `render.yaml`):
- `DATABASE_URL=sqlite:////var/data/portfoliomanager.db`
- `OCR_CMD=/usr/bin/tesseract`
- `OCR_LANG=eng+por`

Para usar **Postgres no Render**, defina `DATABASE_URL` no painel do serviço
(isso sobrescreve o valor do `render.yaml`).

Configuração recomendada no Render (General-db compartilhado):
- `DATABASE_URL` = **Internal Database URL** do `General-db`
- `DB_SCHEMA=portfolio_manager`
- `ENFORCE_DB_SCHEMA=true`

Para um guia completo de produção, veja `docs/PRODUCTION.md`.

## Banco de dados
Local padrão:
```
data/portfoliomanager.db
```
Se mover o arquivo, ajuste `DATABASE_URL` no `.env`.

Para usar o **Postgres do Render localmente**:
1. Copie o **External Database URL** no Render.
2. No `.env` local:
   ```
   DATABASE_URL=postgresql://...
   ```
3. Rode o app normalmente.

## Onde ficam as coisas (atalhos rápidos)
- **Configuração**: `.env`
- **Configuração central em código**: `app/core/settings.py`
- **Modelos e DB**: `app/database.py`
- **Casos de uso (regra de negócio)**: `app/application/`
- **Rotas HTTP**: `app/routers/`
- **Templates (HTML)**: `app/templates/`
- **Serviços (preços/OCR)**: `app/services/`
- **Logs**: `var/logs/`
- **Runtime (PID/porta/log do Uvicorn)**: `var/.run/`

## Logs
```
var/logs/
```

## Uvicorn
Arquivos runtime:
```
var/.run/
```
O script `devctl.sh` usa este caminho por padrão.

## Housekeeping (limpeza segura)
Script:
```bash
./scripts/maintenance/housekeeping.sh
```

Comportamento:
- padrão: `dry-run` (apenas simula)
- remoção real: `--apply`
- logs de runtime: `--with-run-logs`
- logs de aplicação/OCR: `--with-app-logs`
- uploads temporários: `--with-upload-cache`
- limitar por idade: `--older-than-days N`

Exemplo recomendado:
```bash
./scripts/maintenance/housekeeping.sh --apply --with-upload-cache --older-than-days 7
```

## Backup
Sugestão simples:
```bash
cp data/portfoliomanager.db data/backup-$(date +%Y%m%d).db
```
