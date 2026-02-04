# app/services/financial_data.py
# Módulo para buscar dados financeiros de APIs externas

import yfinance as yf
from typing import Optional, Dict, Any
from datetime import datetime

def get_current_price(ticker: str) -> Optional[float]:
    """
    Busca o preço atual de um ativo usando Yahoo Finance.

    Args:
        ticker: Símbolo do ativo (ex: "AAPL", "BTC-USD")

    Returns:
        float: Preço atual ou None se não encontrado
    """
    try:
        stock = yf.Ticker(ticker)
        # Tenta obter preço atual via fast_info
        info = stock.fast_info
        if hasattr(info, 'last_price') and info.last_price:
            return float(info.last_price)
        # Fallback: busca histórico do último dia
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return None
    except Exception as e:
        print(f"Erro ao buscar preço de {ticker}: {e}")
        return None

def get_asset_info(ticker: str) -> Dict[str, Any]:
    """
    Busca informações detalhadas de um ativo.

    Args:
        ticker: Símbolo do ativo

    Returns:
        dict: Informações do ativo (nome, preço, variação, etc.)
    """
    try:
        stock = yf.Ticker(ticker)
        current_price = get_current_price(ticker)

        # Busca histórico para calcular variação
        hist = stock.history(period="5d")
        variation_5d = None
        if not hist.empty and len(hist) >= 2:
            price_5d_ago = hist['Close'].iloc[0]
            if current_price and price_5d_ago:
                variation_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100

        return {
            "ticker": ticker,
            "name": stock.info.get("shortName", ticker),
            "current_price": current_price,
            "variation_5d_percent": variation_5d,
            "currency": stock.info.get("currency", "USD"),
            "last_updated": datetime.now()
        }
    except Exception as e:
        print(f"Erro ao buscar info de {ticker}: {e}")
        return {
            "ticker": ticker,
            "name": ticker,
            "current_price": None,
            "variation_5d_percent": None,
            "currency": "USD",
            "last_updated": datetime.now()
        }
