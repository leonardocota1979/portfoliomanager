# app/routers/search.py
"""
Router de Search/Validação de Tickers

Valida formato de ticker sem buscar preço (performance).
A busca de preço é feita depois pelo price_service.
"""

from fastapi import APIRouter, HTTPException
import re

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


# Padrões de ticker válidos
TICKER_PATTERNS = {
    'us': r'^[A-Z]{1,5}$',  # AAPL, MSFT, etc.
    'us_class': r'^[A-Z]{1,5}\.[A-Z]$',  # BRK.A, BRK.B
    'br': r'^[A-Z]{4}[0-9]{1,2}\.SA$',  # PETR4.SA, VALE3.SA
    'crypto': r'^[A-Z]{2,10}-[A-Z]{3}$',  # BTC-USD, ETH-BRL
    'crypto_compact': r'^[A-Z]{2,10}[A-Z]{3}$',  # BTCUSD, ETHBRL
    'etf': r'^[A-Z]{2,5}$',  # SPY, QQQ, IVV
}


def validate_ticker_format(ticker: str) -> tuple:
    """
    Valida o formato do ticker.
    Retorna: (válido, ticker_normalizado, tipo, erro)
    """
    if not ticker:
        return False, "", "", "Ticker vazio"
    
    ticker = ticker.upper().strip()
    
    # Remove caracteres especiais exceto . e -
    ticker = re.sub(r'[^\w\.\-]', '', ticker)
    
    if len(ticker) < 1:
        return False, "", "", "Ticker muito curto"
    
    if len(ticker) > 20:
        return False, "", "", "Ticker muito longo"
    
    # Detecta tipo
    if ticker.endswith('.SA'):
        if re.match(TICKER_PATTERNS['br'], ticker):
            return True, ticker, "br", ""
        else:
            return False, ticker, "br", "Formato BR inválido. Use: XXXX9.SA (ex: PETR4.SA)"
    
    if '-' in ticker:
        if re.match(TICKER_PATTERNS['crypto'], ticker):
            return True, ticker, "crypto", ""
        else:
            return False, ticker, "crypto", "Formato crypto inválido. Use: XXX-USD (ex: BTC-USD)"

    if re.match(TICKER_PATTERNS['crypto_compact'], ticker):
        # Normaliza para formato com hífen
        normalized = f"{ticker[:-3]}-{ticker[-3:]}"
        return True, normalized, "crypto", ""
    
    if '.' in ticker:
        if re.match(TICKER_PATTERNS['us_class'], ticker):
            return True, ticker, "us", ""
        else:
            return False, ticker, "us", "Formato inválido"
    
    if re.match(TICKER_PATTERNS['us'], ticker):
        return True, ticker, "us", ""
    
    # Aceita outros formatos genéricos
    if re.match(r'^[A-Z0-9]{1,10}$', ticker):
        return True, ticker, "unknown", ""
    
    return False, ticker, "", "Formato de ticker não reconhecido"


@router.get("/validate/{ticker}")
def validate_ticker(ticker: str):
    """
    Valida o formato de um ticker.
    
    Não busca preço - apenas valida formato.
    
    Retorna:
    - valid: bool
    - ticker: ticker normalizado
    - type: tipo detectado (us, br, crypto, etf)
    - error: mensagem de erro se inválido
    - suggestions: sugestões de formato
    """
    valid, normalized, ticker_type, error = validate_ticker_format(ticker)
    
    suggestions = []
    if not valid:
        suggestions = [
            "US Stocks: AAPL, MSFT, GOOGL",
            "BR Stocks: PETR4.SA, VALE3.SA, ITUB4.SA",
            "Crypto: BTC-USD, ETH-USD, SOL-USD",
            "ETFs: SPY, QQQ, IVV"
        ]
    
    return {
        "valid": valid,
        "ticker": normalized,
        "type": ticker_type,
        "error": error,
        "suggestions": suggestions
    }


@router.get("/suggestions")
def get_ticker_suggestions(query: str = ""):
    """
    Retorna sugestões de tickers baseado na query.
    
    Popular para ajudar usuários a encontrar tickers.
    """
    # Tickers populares por categoria
    popular = {
        "us_stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "V", "WMT"],
        "br_stocks": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA", "WEGE3.SA", "MGLU3.SA"],
        "crypto": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD"],
        "etfs": ["SPY", "QQQ", "IVV", "VTI", "VOO", "ARKK", "DIA"]
    }
    
    if not query:
        return popular
    
    query = query.upper()
    
    # Filtra por query
    filtered = {}
    for category, tickers in popular.items():
        matches = [t for t in tickers if query in t]
        if matches:
            filtered[category] = matches
    
    return filtered if filtered else popular
