# Produção (padrão profissional)

Este guia cobre **deploy profissional** e **boas práticas mínimas**.

## Checklist obrigatório
1. `SECRET_KEY` definido (não usar padrão de desenvolvimento).
2. `DATABASE_URL` apontando para banco persistente (Postgres recomendado).
3. HTTPS ativo (Render já fornece).
4. Backup automático do banco.
5. Logs acessíveis (Render ou VPS).

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
Crie um Postgres no Render e substitua `DATABASE_URL`.

### 4.1) Seed automático de classes globais
No primeiro boot, o sistema cria classes globais padrão automaticamente
(Stocks, Bonds, REITs, Crypto, Commodities, Reserva de Valor).

### 5) Deploy
Finalize o deploy e acesse a URL pública fornecida pelo Render.

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
