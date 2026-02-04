# app/services/price_service.py
"""
Serviço de Preços Multi-Fonte

Fontes de dados:
1. Finnhub (US stocks, ETFs) - 60 calls/min free
2. Brapi (BR stocks .SA) - gratuito para PETR4, VALE3, MGLU3, ITUB4
3. CoinGecko (Crypto) - 30 calls/min free
4. CoinCap (Crypto fallback, USD)
5. Alpha Vantage (backup) - 5 calls/min free
6. TwelveData (backup) - requer API key
7. FinancialModelingPrep (backup) - requer API key
8. Stooq (US stocks fallback, gratuito)

Auto-refresh: A cada 1 minuto no frontend
"""

import httpx
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import re


class PriceService:
    """Serviço para buscar preços de ativos de múltiplas fontes."""
    
    # Configuração das APIs
    FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    BRAPI_BASE_URL = "https://brapi.dev/api"
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    COINCAP_BASE_URL = "https://api.coincap.io/v2"
    YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
    TWELVEDATA_BASE_URL = "https://api.twelvedata.com/price"
    FMP_BASE_URL = "https://financialmodelingprep.com/api/v3/quote-short"
    
    # Mapeamento de crypto tickers para IDs do CoinGecko
    CRYPTO_ID_MAP = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "SOL": "solana",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "SHIB": "shiba-inu",
        "LTC": "litecoin",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "XLM": "stellar",
        "ALGO": "algorand",
        "VET": "vechain",
        "FIL": "filecoin",
        "NEAR": "near",
    }
    
    # Ações BR gratuitas no brapi (sem token)
    BRAPI_FREE_TICKERS = ["PETR4", "VALE3", "MGLU3", "ITUB4"]
    
    def __init__(self, finnhub_key: str = None, alphavantage_key: str = None, brapi_token: str = None,
                 twelvedata_key: str = None, fmp_key: str = None):
        self.finnhub_key = finnhub_key
        self.alphavantage_key = alphavantage_key
        self.brapi_token = brapi_token
        self.twelvedata_key = twelvedata_key
        self.fmp_key = fmp_key
        self.cache: Dict[str, Tuple[float, datetime, str]] = {}  # ticker -> (price, timestamp, source)
        self.cache_ttl = 60  # 1 minuto
    
    def _is_cache_valid(self, ticker: str) -> bool:
        """Verifica se o cache ainda é válido."""
        if ticker not in self.cache:
            return False
        _, timestamp, _ = self.cache[ticker]
        return (datetime.now() - timestamp).seconds < self.cache_ttl
    
    def _detect_ticker_type(self, ticker: str) -> str:
        """
        Detecta o tipo de ticker:
        - 'br' para ações brasileiras (.SA)
        - 'crypto' para criptomoedas (-USD, -BRL, etc)
        - 'us' para ações americanas e ETFs
        """
        ticker_upper = ticker.upper().strip()
        
        if ticker_upper.endswith('.SA'):
            return 'br'
        
        # Verifica se é crypto (formato: BTC-USD, ETH-BRL, etc)
        if '-' in ticker_upper:
            base = ticker_upper.split('-')[0]
            if base in self.CRYPTO_ID_MAP:
                return 'crypto'
        
        # Verifica se é crypto sem sufixo
        if ticker_upper in self.CRYPTO_ID_MAP:
            return 'crypto'
        
        return 'us'
    
    async def get_price(self, ticker: str) -> Tuple[float, str, str]:
        """
        Busca o preço de um ticker.
        Retorna: (preço, fonte, erro_ou_vazio)
        """
        ticker = ticker.upper().strip()
        # Normaliza crypto sem hífen (ex: BTCUSD -> BTC-USD)
        if "-" not in ticker and len(ticker) > 3:
            suffix = ticker[-3:]
            base = ticker[:-3]
            if suffix in ["USD", "BRL", "EUR"] and base in self.CRYPTO_ID_MAP:
                ticker = f"{base}-{suffix}"
        
        # Verifica cache
        if self._is_cache_valid(ticker):
            price, _, source = self.cache[ticker]
            return price, source, ""
        
        ticker_type = self._detect_ticker_type(ticker)
        price = 0.0
        source = ""
        error = ""
        
        try:
            if ticker_type == 'br':
                price, source, error = await self._get_br_price(ticker)
            elif ticker_type == 'crypto':
                price, source, error = await self._get_crypto_price(ticker)
            else:
                price, source, error = await self._get_us_price(ticker)
            
            # Atualiza cache se obteve preço
            if price > 0:
                self.cache[ticker] = (price, datetime.now(), source)
            
            return price, source, error
            
        except Exception as e:
            return 0.0, "", f"Erro geral: {str(e)}"
    
    async def _get_br_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço de ação brasileira via Brapi."""
        # Remove .SA para a API brapi
        clean_ticker = ticker.replace('.SA', '').upper()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.BRAPI_BASE_URL}/quote/{clean_ticker}"
                params = {}
                
                # Usa token se disponível e não é ticker gratuito
                if self.brapi_token and clean_ticker not in self.BRAPI_FREE_TICKERS:
                    params['token'] = self.brapi_token
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data and len(data['results']) > 0:
                        result = data['results'][0]
                        price = result.get('regularMarketPrice', 0)
                        if price and price > 0:
                            return float(price), "Brapi", ""
                
                return 0.0, "", f"Brapi: Ticker {clean_ticker} não encontrado"
                
        except httpx.TimeoutException:
            return 0.0, "", "Brapi: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"Brapi: {str(e)}"
    
    async def _get_crypto_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço de crypto via CoinGecko."""
        # Extrai base ticker (BTC-USD -> BTC)
        base_ticker = ticker.split('-')[0].upper()
        currency = 'usd'
        
        if '-' in ticker:
            currency_part = ticker.split('-')[1].lower()
            if currency_part in ['usd', 'brl', 'eur']:
                currency = currency_part
        
        coin_id = self.CRYPTO_ID_MAP.get(base_ticker)
        if not coin_id:
            coin_id = await self._resolve_coingecko_id(base_ticker)
            if not coin_id:
                return 0.0, "", f"CoinGecko: Crypto {base_ticker} não suportado"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.COINGECKO_BASE_URL}/simple/price"
                params = {
                    'ids': coin_id,
                    'vs_currencies': currency
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if coin_id in data and currency in data[coin_id]:
                        price = data[coin_id][currency]
                        if price and price > 0:
                            return float(price), "CoinGecko", ""
                
                # Fallback: CoinCap (somente USD)
                if currency == "usd":
                    return await self._get_crypto_price_coincap(base_ticker)
                return 0.0, "", f"CoinGecko: Preço não encontrado para {ticker}"
                
        except httpx.TimeoutException:
            return 0.0, "", "CoinGecko: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"CoinGecko: {str(e)}"

    async def _resolve_coingecko_id(self, base_ticker: str) -> Optional[str]:
        """Tenta resolver o ID do CoinGecko usando o endpoint de busca."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.COINGECKO_BASE_URL}/search"
                response = await client.get(url, params={"query": base_ticker})
                if response.status_code == 200:
                    data = response.json()
                    coins = data.get("coins", [])
                    if coins:
                        return coins[0].get("id")
        except Exception:
            return None
        return None

    async def _get_crypto_price_coincap(self, base_ticker: str) -> Tuple[float, str, str]:
        """Fallback de crypto via CoinCap (USD)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.COINCAP_BASE_URL}/assets"
                response = await client.get(url, params={"search": base_ticker})
                if response.status_code == 200:
                    data = response.json()
                    assets = data.get("data", [])
                    if assets:
                        price = assets[0].get("priceUsd")
                        if price:
                            return float(price), "CoinCap", ""
            return 0.0, "", f"CoinCap: Preço não encontrado para {base_ticker}"
        except httpx.TimeoutException:
            return 0.0, "", "CoinCap: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"CoinCap: {str(e)}"
    
    async def _get_us_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço de ação US via Finnhub (com fallback para Alpha Vantage)."""
        
        # Tenta Finnhub primeiro
        if self.finnhub_key:
            price, source, error = await self._get_finnhub_price(ticker)
            if price > 0:
                return price, source, error
        
        # Fallback: Alpha Vantage
        if self.alphavantage_key:
            price, source, error = await self._get_alphavantage_price(ticker)
            if price > 0:
                return price, source, error

        # Fallback: TwelveData
        if self.twelvedata_key:
            price, source, error = await self._get_twelvedata_price(ticker)
            if price > 0:
                return price, source, error

        # Fallback: FMP
        if self.fmp_key:
            price, source, error = await self._get_fmp_price(ticker)
            if price > 0:
                return price, source, error

        # Fallback: Stooq (gratuito, sem chave)
        price, source, error = await self._get_stooq_price(ticker)
        if price > 0:
            return price, source, error

        # Fallback final: Yahoo quote endpoint (sem yfinance)
        price, source, error = await self._get_yahoo_quote_price(ticker)
        if price > 0:
            return price, source, error

        # Se não tem API keys e fallbacks falharam, retorna erro
        return 0.0, "", "Não foi possível obter preço para ações/ETFs. Configure FINNHUB_KEY ou ALPHAVANTAGE_KEY para melhor cobertura."
    
    async def _get_finnhub_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço via Finnhub."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.FINNHUB_BASE_URL}/quote"
                params = {
                    'symbol': ticker,
                    'token': self.finnhub_key
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    # 'c' é o preço atual (current)
                    price = data.get('c', 0)
                    if price and price > 0:
                        return float(price), "Finnhub", ""
                
                return 0.0, "", f"Finnhub: Preço não encontrado para {ticker}"
                
        except httpx.TimeoutException:
            return 0.0, "", "Finnhub: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"Finnhub: {str(e)}"
    
    async def _get_alphavantage_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço via Alpha Vantage (backup)."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    'function': 'GLOBAL_QUOTE',
                    'symbol': ticker,
                    'apikey': self.alphavantage_key
                }
                
                response = await client.get(self.ALPHAVANTAGE_BASE_URL, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'Global Quote' in data:
                        quote = data['Global Quote']
                        price = quote.get('05. price', 0)
                        if price:
                            return float(price), "AlphaVantage", ""
                
                return 0.0, "", f"AlphaVantage: Preço não encontrado para {ticker}"
                
        except httpx.TimeoutException:
            return 0.0, "", "AlphaVantage: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"AlphaVantage: {str(e)}"

    async def _get_stooq_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço via Stooq (CSV)."""
        try:
            url = "https://stooq.com/q/l/"
            # Tenta múltiplos formatos para melhorar cobertura (REITs, ETFs, tickers com ponto)
            base = ticker.lower()
            variants = [
                f"{base}.us",
                base,
                base.replace(".", "-"),
                f"{base.replace('.', '-')}.us",
            ]

            async with httpx.AsyncClient(timeout=10.0) as client:
                for symbol in variants:
                    params = {"s": symbol, "i": "d"}
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        continue
                    # CSV: Date,Open,High,Low,Close,Volume
                    lines = response.text.strip().splitlines()
                    if len(lines) >= 2:
                        last_line = lines[-1]
                        parts = last_line.split(",")
                        if len(parts) >= 5:
                            close_price = parts[4]
                            if close_price and close_price != "N/A":
                                return float(close_price), "Stooq", ""
            return 0.0, "", f"Stooq: Preço não encontrado para {ticker}"
        except httpx.TimeoutException:
            return 0.0, "", "Stooq: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"Stooq: {str(e)}"

    async def _get_yahoo_quote_price(self, ticker: str) -> Tuple[float, str, str]:
        """Fallback via endpoint de quote do Yahoo (sem yfinance)."""
        try:
            params = {"symbols": ticker}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.YAHOO_BASE_URL, params=params, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("quoteResponse", {}).get("result", [])
                    if result:
                        quote = result[0]
                        price = quote.get("regularMarketPrice") or quote.get("postMarketPrice") or quote.get("preMarketPrice")
                        if price and price > 0:
                            return float(price), "YahooQuote", ""
                return 0.0, "", f"YahooQuote: Preço não encontrado para {ticker}"
        except httpx.TimeoutException:
            return 0.0, "", "YahooQuote: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"YahooQuote: {str(e)}"

    async def _get_twelvedata_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço via TwelveData."""
        try:
            params = {"symbol": ticker, "apikey": self.twelvedata_key}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.TWELVEDATA_BASE_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    price = data.get("price")
                    if price:
                        return float(price), "TwelveData", ""
            return 0.0, "", f"TwelveData: Preço não encontrado para {ticker}"
        except httpx.TimeoutException:
            return 0.0, "", "TwelveData: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"TwelveData: {str(e)}"

    async def _get_fmp_price(self, ticker: str) -> Tuple[float, str, str]:
        """Busca preço via FinancialModelingPrep."""
        try:
            params = {"apikey": self.fmp_key}
            url = f"{self.FMP_BASE_URL}/{ticker}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and data:
                        price = data[0].get("price")
                        if price:
                            return float(price), "FMP", ""
            return 0.0, "", f"FMP: Preço não encontrado para {ticker}"
        except httpx.TimeoutException:
            return 0.0, "", "FMP: Timeout na requisição"
        except Exception as e:
            return 0.0, "", f"FMP: {str(e)}"
    
    async def get_prices_batch(self, tickers: List[str]) -> Dict[str, Tuple[float, str, str]]:
        """
        Busca preços de múltiplos tickers em paralelo.
        Retorna: {ticker: (preço, fonte, erro)}
        """
        tasks = [self.get_price(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                prices[ticker] = (0.0, "", str(result))
            else:
                prices[ticker] = result
        
        return prices

    async def get_price_candidates(self, ticker: str) -> List[Tuple[float, str]]:
        """Retorna múltiplas cotações (preço, fonte) quando disponíveis."""
        ticker = ticker.upper().strip()
        if "-" not in ticker and len(ticker) > 3:
            suffix = ticker[-3:]
            base = ticker[:-3]
            if suffix in ["USD", "BRL", "EUR"] and base in self.CRYPTO_ID_MAP:
                ticker = f"{base}-{suffix}"
        ticker_type = self._detect_ticker_type(ticker)
        candidates: List[Tuple[float, str]] = []

        if ticker_type == "crypto":
            price, source, _ = await self._get_crypto_price(ticker)
            if price > 0:
                candidates.append((price, source))
            # CoinCap direto como fallback
            base = ticker.split("-")[0]
            price, source, _ = await self._get_crypto_price_coincap(base)
            if price > 0:
                candidates.append((price, source))
            return candidates

        if ticker_type == "br":
            price, source, _ = await self._get_br_price(ticker)
            if price > 0:
                candidates.append((price, source))
            return candidates

        # US/ETF/REIT
        if self.finnhub_key:
            price, source, _ = await self._get_finnhub_price(ticker)
            if price > 0:
                candidates.append((price, source))
        if self.alphavantage_key:
            price, source, _ = await self._get_alphavantage_price(ticker)
            if price > 0:
                candidates.append((price, source))
        if self.twelvedata_key:
            price, source, _ = await self._get_twelvedata_price(ticker)
            if price > 0:
                candidates.append((price, source))
        if self.fmp_key:
            price, source, _ = await self._get_fmp_price(ticker)
            if price > 0:
                candidates.append((price, source))
        price, source, _ = await self._get_stooq_price(ticker)
        if price > 0:
            candidates.append((price, source))
        price, source, _ = await self._get_yahoo_quote_price(ticker)
        if price > 0:
            candidates.append((price, source))

        return candidates

    async def get_price_consensus(self, ticker: str) -> Tuple[float, str, bool]:
        """
        Retorna preço de consenso (mediana), fonte e flag de divergência.
        Divergência:
          - mercado tradicional: >0.1%
          - crypto: >1%
        """
        candidates = await self.get_price_candidates(ticker)
        if not candidates:
            return 0.0, "", True

        prices = [p for p, _ in candidates]
        prices_sorted = sorted(prices)
        mid = len(prices_sorted) // 2
        median = prices_sorted[mid] if len(prices_sorted) % 2 == 1 else (prices_sorted[mid - 1] + prices_sorted[mid]) / 2

        # Divergência
        min_p, max_p = min(prices_sorted), max(prices_sorted)
        if median == 0:
            return 0.0, "", True

        ticker_type = self._detect_ticker_type(ticker)
        threshold = 0.01 if ticker_type == "crypto" else 0.001
        divergence = (max_p - min_p) / median if median > 0 else 0
        diverged = divergence > threshold

        # Fonte: concatena as fontes usadas
        sources = ",".join(sorted(set(src for _, src in candidates)))
        return median, sources, diverged

    async def validate_providers(self) -> Dict[str, str]:
        """
        Testa os provedores configurados sem expor chaves.
        Retorna status por provedor.
        """
        results: Dict[str, str] = {}
        # Finnhub
        if self.finnhub_key:
            price, _, error = await self._get_finnhub_price("AAPL")
            results["finnhub"] = "ok" if price > 0 else f"erro: {error}"
        else:
            results["finnhub"] = "não configurado"

        # Alpha Vantage
        if self.alphavantage_key:
            price, _, error = await self._get_alphavantage_price("AAPL")
            results["alphavantage"] = "ok" if price > 0 else f"erro: {error}"
        else:
            results["alphavantage"] = "não configurado"

        # TwelveData
        if self.twelvedata_key:
            price, _, error = await self._get_twelvedata_price("AAPL")
            results["twelvedata"] = "ok" if price > 0 else f"erro: {error}"
        else:
            results["twelvedata"] = "não configurado"

        # FMP
        if self.fmp_key:
            price, _, error = await self._get_fmp_price("AAPL")
            results["fmp"] = "ok" if price > 0 else f"erro: {error}"
        else:
            results["fmp"] = "não configurado"

        # Stooq (sem chave)
        price, _, error = await self._get_stooq_price("AAPL")
        results["stooq"] = "ok" if price > 0 else f"erro: {error}"

        # Yahoo Quote (sem chave)
        price, _, error = await self._get_yahoo_quote_price("AAPL")
        results["yahoo_quote"] = "ok" if price > 0 else f"erro: {error}"

        return results
    
    def validate_ticker_format(self, ticker: str) -> Tuple[bool, str, str]:
        """
        Valida o formato do ticker.
        Retorna: (válido, ticker_normalizado, erro)
        """
        if not ticker or len(ticker) < 1:
            return False, "", "Ticker vazio"
        
        ticker = ticker.upper().strip()
        
        # Remove caracteres inválidos
        ticker = re.sub(r'[^\w\-\.]', '', ticker)
        
        if len(ticker) > 20:
            return False, "", "Ticker muito longo (max 20 caracteres)"
        
        return True, ticker, ""


# Instância global do serviço
_price_service: Optional[PriceService] = None


def get_price_service(
    finnhub_key: str = None,
    alphavantage_key: str = None,
    brapi_token: str = None,
    twelvedata_key: str = None,
    fmp_key: str = None
) -> PriceService:
    """Retorna instância singleton do serviço de preços."""
    global _price_service
    
    if _price_service is None:
        import os
        _price_service = PriceService(
            finnhub_key=finnhub_key or os.getenv('FINNHUB_KEY'),
            alphavantage_key=alphavantage_key or os.getenv('ALPHAVANTAGE_KEY'),
            brapi_token=brapi_token or os.getenv('BRAPI_TOKEN'),
            twelvedata_key=twelvedata_key or os.getenv('TWELVEDATA_KEY'),
            fmp_key=fmp_key or os.getenv('FMP_KEY')
        )
    
    return _price_service


# Função de conveniência para uso síncrono
def get_price_sync(ticker: str) -> Tuple[float, str, str]:
    """Versão síncrona de get_price para uso em contextos não-async."""
    service = get_price_service()
    return asyncio.run(service.get_price(ticker))
