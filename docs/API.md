# API e Integrações

## Endpoints principais
- `GET /portfolios/list` — lista carteiras (HTML)
- `GET /dashboard?portfolio_id=ID` — dashboard (HTML)
- `POST /dashboard/update-prices/{portfolio_id}` — atualiza preços
- `POST /imports/preview` — pré-visualização OCR
- `POST /imports/confirm` — confirma importação

## Observações
- As rotas HTML retornam páginas renderizadas (Jinja2).
- As rotas de ação usam JSON (fetch no frontend).

## Integrações de preços
O sistema busca preços com múltiplas fontes e aplica consenso:
- Finnhub
- Alpha Vantage
- Yahoo (fallback)
- Stooq (fallback)
- CoinGecko / CoinCap (crypto)

## OCR
Tesseract:
- `OCR_CMD=/opt/homebrew/bin/tesseract`
- `OCR_LANG=eng+por`

## Regras de consenso
- Mercado tradicional: divergência máx 0,1%
- Crypto: divergência máx 1%
