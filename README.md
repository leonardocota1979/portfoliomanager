# Portfolio Manager v2 - Instruções de Atualização

## Documentação completa
Veja `docs/README.md` para guias detalhados.

## Deploy (Render)
Há um `render.yaml` pronto para publicação no Render.

## 📋 Resumo das Alterações

### 1. Nova Lógica de Valor do Portfolio
- O valor total é **FIXO** (definido pelo usuário na criação/edição)
- **NÃO** é calculado pela soma dos ativos
- Cada classe de ativos tem um valor alvo baseado no % meta
- O que não for alocado aparece como CASH

### 2. Consulta de Preços Multi-Fonte
- **Finnhub** (US stocks, ETFs) - 60 calls/min
- **Brapi** (BR stocks .SA) - gratuito para PETR4, VALE3, MGLU3, ITUB4
- **CoinGecko** (Crypto) - 30 calls/min

### 3. Auto-Refresh
- Preços atualizados automaticamente a cada **1 minuto**
- Indicador de status no dashboard

### 4. Hierarquia Visual
- Classes de ativos como cabeçalhos expansíveis
- Ativos agrupados por classe
- CASH restante por classe

### 5. Ordenação e Filtros
- Clique nas colunas para ordenar (▲/▼)
- Filtros por texto e status

### 6. Gráficos
- **Pizza** - Alocação por classe (clicável)
- **Barras** - Meta vs Real com alertas de desvio

### 7. Novos Endpoints
- `POST /dashboard/update-prices/{portfolio_id}` - Atualiza preços
- `GET /dashboard/charts/{portfolio_id}` - Dados para gráficos
- `PUT /assets/update-price/{ticker}` - Preço manual

---

## 🚀 Instalação

### 1. Backup
```bash
cp -r app app.backup
cp portfoliomanager.db portfoliomanager.db.backup
```

### 2. Instalar dependências
```bash
pip install httpx --break-system-packages
```

### 3. Copiar arquivos
Substitua os arquivos existentes pelos novos:

| Arquivo | Destino |
|---------|---------|
| `app/database.py` | `app/database.py` |
| `app/routers/dashboard.py` | `app/routers/dashboard.py` |
| `app/routers/portfolios.py` | `app/routers/portfolios.py` |
| `app/routers/assets.py` | `app/routers/assets.py` |
| `app/routers/portfolio_assets.py` | `app/routers/portfolio_assets.py` |
| `app/routers/search.py` | `app/routers/search.py` |
| `app/services/price_service.py` | `app/services/price_service.py` (criar pasta) |
| `app/templates/dashboard.html` | `app/templates/dashboard.html` |
| `app/templates/portfolio_list.html` | `app/templates/portfolio_list.html` |

### 4. Executar migração
```bash
python scripts/migrate_add_price_columns.py
```

### 5. Configurar API Keys (opcional mas recomendado)
Crie um arquivo `.env` na raiz:
```env
FINNHUB_KEY=sua_chave_finnhub
ALPHAVANTAGE_KEY=sua_chave_alphavantage  # backup
BRAPI_TOKEN=seu_token_brapi  # para ações BR além das gratuitas
TWELVEDATA_KEY=sua_chave_twelvedata
FMP_KEY=sua_chave_fmp
SECRET_KEY=uma_chave_forte_para_jwt
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./portfoliomanager.db
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

**Obter chaves:**
- Finnhub: https://finnhub.io/register (gratuito, 60 calls/min)
- Brapi: https://brapi.dev (gratuito para PETR4, VALE3, MGLU3, ITUB4)

### 6. Reiniciar servidor
```bash
uvicorn app.main:app --reload
```

---

## 📥 Importação via OCR (prints)

Pré-requisitos (macOS):
```bash
brew install tesseract
```

Após instalar, acesse:
```
/imports
```

---

## 👤 Criar/Promover Admin

Para criar um usuário admin (ou promover um existente):

```bash
python scripts/create_admin.py --username admin --password sua_senha --email admin@local
```

Para apenas promover um usuário existente para admin:

```bash
python scripts/create_admin.py --username admin --make-admin-only
```

---

## 📁 Estrutura de Arquivos

```
app/
├── database.py          # Modelos (atualizado)
├── routers/
│   ├── dashboard.py     # Dashboard (refatorado)
│   ├── portfolios.py    # Portfolios (corrigido)
│   ├── assets.py        # Assets (corrigido)
│   ├── portfolio_assets.py  # (corrigido)
│   └── search.py        # Validação de tickers
├── services/
│   └── price_service.py # Serviço de preços (NOVO)
└── templates/
    ├── dashboard.html   # Dashboard (refatorado)
    └── portfolio_list.html  # Lista (com botão Editar)
```

---

## 🔧 Funcionalidades

### Dashboard
- Resumo do portfolio com valores: Definido, Alocado, CASH
- Gráfico de Pizza 3D (clicável)
- Gráfico de Barras (Meta vs Real)
- Tabela hierárquica por classe de ativos
- Ordenação e filtros
- Auto-refresh de preços (1 min)
- Edição de portfolio (valor total, moeda)
- Edição de ativos (quantidade, % meta, preço manual)

### Lista de Carteiras
- Botão "Dashboard" 
- Botão "Editar" (NOVO)
- Botão "Deletar"

### Alertas de Desvio
- ⚠️ **SUB-ALOCADO**: Real < 90% da Meta (amarelo)
- 🔶 **SOBRE-ALOCADO**: Real > 110% da Meta (laranja)
- 🟢 **OK**: Entre 90% e 110%

---

## ⚠️ Notas Importantes

1. **Valor Total Fixo**: O valor do portfolio é definido manualmente e não muda com alocações
2. **APIs Gratuitas**: Têm limites de requisições - o auto-refresh de 1 min respeita isso
3. **Preço Manual**: Use quando a API não encontrar o preço
4. **Backup**: Sempre faça backup antes de atualizar

---

## 🐛 Problemas Comuns

### "Ticker não encontrado"
- Verifique o formato: AAPL (US), PETR4.SA (BR), BTC-USD (crypto)
- Use a validação: `/search/validate/{ticker}`

### Preços não atualizam
- Verifique as API keys no `.env`
- Teste manualmente: `POST /dashboard/update-prices/{id}`

### Quantidade multiplicada por 1000
- Use ponto para decimais: `10.5` não `10,5`
