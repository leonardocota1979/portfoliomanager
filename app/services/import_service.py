"""
Serviço de importação com OCR (Tesseract) e parsing de posições.
"""

from __future__ import annotations

import re
import subprocess
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import logging
from app.core.settings import get_settings


SETTINGS = get_settings()

# Diretório único de logs operacionais do projeto.
# Mantido em `var/logs` para separar runtime, dados e código.
LOG_DIR = SETTINGS.log_dir
LOG_DIR.mkdir(parents=True, exist_ok=True)

ocr_logger = logging.getLogger("import_ocr")
imp_logger = logging.getLogger("import_flow")

if not ocr_logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "ocr.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    ocr_logger.addHandler(handler)
    ocr_logger.setLevel(logging.INFO)

if not imp_logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "imports.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    imp_logger.addHandler(handler)
    imp_logger.setLevel(logging.INFO)


@dataclass
class ParsedPosition:
    ticker: str
    name: str
    quantity: float
    price: Optional[float] = None


CRYPTO_NAME_MAP = {
    "BITCOIN": ("BTC", "Bitcoin"),
    "BTC": ("BTC", "Bitcoin"),
    "ETHEREUM": ("ETH", "Ethereum"),
    "ETH": ("ETH", "Ethereum"),
    "SOLANA": ("SOL", "Solana"),
    "SOL": ("SOL", "Solana"),
}


TOP_CURRENCIES = ["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "CNY", "BRL"]

CURRENCY_HINTS = {
    "USD": [r"\\$", r"USD"],
    "BRL": [r"R\\$", r"BRL"],
    "EUR": [r"€", r"EUR"],
    "GBP": [r"£", r"GBP"],
    "JPY": [r"¥", r"JPY"],
    "CAD": [r"C\\$", r"CAD"],
    "AUD": [r"A\\$", r"AUD"],
    "NZD": [r"NZ\\$", r"NZD"],
    "CHF": [r"CHF"],
    "CNY": [r"CNY", r"CN¥"],
}


def _resolve_tesseract_cmd() -> Optional[str]:
    """Resolve o binário do tesseract em ambientes macOS."""
    env_cmd = SETTINGS.ocr_cmd
    if env_cmd:
        return env_cmd
    found = shutil.which("tesseract")
    if found:
        return found
    # caminhos comuns no macOS
    for path in ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"):
        if Path(path).exists():
            return path
    return None


def run_tesseract(image_path: Path) -> str:
    """
    Executa OCR via Tesseract e retorna o texto.
    """
    lang = SETTINGS.ocr_lang
    tesseract_cmd = _resolve_tesseract_cmd()
    if not tesseract_cmd:
        ocr_logger.error("OCR erro: tesseract não encontrado no PATH. Defina OCR_CMD.")
        return ""
    cmd = [
        tesseract_cmd,
        str(image_path),
        "stdout",
        "--psm",
        "6",
        "-l",
        lang,
    ]
    try:
        ocr_logger.info("OCR start %s", image_path)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            ocr_logger.error("OCR erro: %s", result.stderr.strip())
            return ""
        text = result.stdout or ""
        ocr_logger.info("OCR ok (%d chars) lang=%s", len(text), lang)
        try:
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            (LOG_DIR / f"ocr_{stamp}.txt").write_text(text, encoding="utf-8")
            (LOG_DIR / "ocr_last.txt").write_text(text, encoding="utf-8")
        except Exception:
            pass
        return text
    except Exception as e:
        ocr_logger.exception("OCR exception: %s", e)
        return ""


def detect_currency(text: str) -> Optional[str]:
    if not text:
        return None
    for code, patterns in CURRENCY_HINTS.items():
        for pat in patterns:
            if re.search(pat, text):
                return code
    return None


def parse_number(val: str) -> Optional[float]:
    if not val:
        return None
    cleaned = val.strip()
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("R$", "")
    try:
        # detect locale: if both . and , exist, use last separator as decimal
        if "." in cleaned and "," in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "")
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None


def parse_positions_hardwallet(text: str) -> List[ParsedPosition]:
    """
    Parser heurístico para prints de hardwallet.
    """
    positions: List[ParsedPosition] = []
    if not text:
        return positions

    def normalize_crypto_qty(raw: str) -> Optional[float]:
        # se não tem separador decimal e é longo, assume 5 casas decimais
        if raw and "." not in raw and "," not in raw and len(raw) >= 6:
            raw = raw[:-5] + "." + raw[-5:]
        return parse_number(raw)

    normalized = re.sub(r"\\s+", " ", text)
    qty_candidates: Dict[str, List[float]] = {}

    # captura direta de quantidade + ticker (ex: 3,81884 BTC)
    direct_matches = re.findall(r"([0-9][0-9\\.,]*)\\s*(BTC|ETH|SOL)", normalized, flags=re.IGNORECASE)
    for num_str, tk in direct_matches:
        ticker = tk.upper()
        val = normalize_crypto_qty(num_str)
        if val is not None:
            qty_candidates.setdefault(ticker, []).append(val)

    # procura por nomes e tickers próximos
    for key, (ticker, name) in CRYPTO_NAME_MAP.items():
        if key not in normalized.upper():
            continue
        pattern = re.compile(rf"{key}(.{{0,160}})", re.IGNORECASE)
        for m in pattern.finditer(normalized):
            window = m.group(1)
            nums = re.findall(r"[0-9][0-9\\.,]*", window)
            for n in nums:
                val = normalize_crypto_qty(n)
                if val is not None:
                    qty_candidates.setdefault(ticker, []).append(val)
    # fallback por linhas
    if not qty_candidates:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            upper = ln.upper()
            for key, (ticker, name) in CRYPTO_NAME_MAP.items():
                if key in upper:
                    nums = re.findall(r"[0-9]+(?:[\\.,][0-9]+)?", ln)
                    for n in nums:
                        val = normalize_crypto_qty(n)
                        if val is not None:
                            qty_candidates.setdefault(ticker, []).append(val)
                    break

    # seleciona a menor quantidade plausível (normalmente a quantidade do ativo)
    for ticker, vals in qty_candidates.items():
        if not vals:
            continue
        qty = min(vals)
        name = CRYPTO_NAME_MAP.get(ticker, (ticker, ticker))[1]
        positions.append(ParsedPosition(ticker=ticker, name=name, quantity=qty))
    return positions


def parse_positions_schwab(text: str) -> List[ParsedPosition]:
    """
    Parser heurístico para prints da Schwab (Symbol/Name, Quantity, Price, Market Value).
    """
    positions: List[ParsedPosition] = []
    if not text:
        return positions

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    symbol_re = re.compile(r"^([A-Z]{1,5}(?:\\.[A-Z])?)\\s+")

    for ln in lines:
        if "Symbol" in ln or "Quantity" in ln or "Market Value" in ln:
            continue
        m = symbol_re.match(ln)
        if not m:
            continue
        symbol = m.group(1)
        # extrai números da linha (qty, price, etc)
        nums = re.findall(r"[0-9]+(?:\\.[0-9]+)?", ln.replace(",", ""))
        qty = None
        price = None
        if len(nums) >= 2:
            qty = parse_number(nums[0])
            price = parse_number(nums[1])
        elif len(nums) == 1:
            qty = parse_number(nums[0])
        if qty is None:
            continue
        positions.append(ParsedPosition(ticker=symbol, name=symbol, quantity=qty, price=price))

    return positions


def parse_positions(text: str, source: str) -> List[ParsedPosition]:
    source = (source or "").lower()
    if source == "hardwallet":
        return parse_positions_hardwallet(text)
    if source == "schwab":
        return parse_positions_schwab(text)
    # fallback tenta ambos
    positions = parse_positions_schwab(text)
    if positions:
        return positions
    return parse_positions_hardwallet(text)
