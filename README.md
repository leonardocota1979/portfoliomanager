# Portfolio Manager

Sistema web para gestão de portfólios com:
- classes de ativos e metas por classe;
- importação OCR de posições (prints);
- atualização de preços multi-fonte;
- dashboard com 3 templates;
- gestão de usuários com perfil admin.

Arquitetura atual:
- monólito modular com separação de camadas (`app/core`, `app/application`, `app/routers`, `app/services`).

## Execução local
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./devctl.sh
```

## Ambiente
Arquivo `.env` (base em `.env.example`):
- `DATABASE_URL=sqlite:///./data/portfoliomanager.db` (local padrão)
- `SECRET_KEY=...`
- `FINNHUB_KEY=...`
- `ALPHAVANTAGE_KEY=...`
- `OCR_CMD=/opt/homebrew/bin/tesseract`
- `OCR_LANG=eng+por`
- `ADMIN_BOOTSTRAP_USER=...`
- `ADMIN_BOOTSTRAP_PASS=...`
- `ADMIN_BOOTSTRAP_EMAIL=...`

## Deploy Render
- Arquivo `render.yaml` pronto para Web Service.
- Para produção com Postgres: sobrescreva `DATABASE_URL` no painel do Render.
- Guia completo: `docs/PRODUCTION.md`.

## Documentação
- Índice geral: `docs/README.md`
- Estrutura de diretórios e padrões: `docs/STRUCTURE.md`
- Arquitetura e fluxos: `docs/ARCHITECTURE.md`
- Operação diária: `docs/OPERATIONS.md`
- Deploy Render + Postgres: `docs/PRODUCTION.md`
