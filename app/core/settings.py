"""
Configuração central da aplicação.

Objetivos:
- Eliminar `os.getenv` espalhado pelo código.
- Padronizar caminhos de runtime/logs/backups.
- Garantir compatibilidade local (SQLite) e produção (Postgres).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Carrega .env independentemente da ordem de import dos módulos.
load_dotenv()


def _parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(database_url: str) -> str:
    # SQLAlchemy 2 usa `postgresql://`; alguns provedores entregam `postgres://`.
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _default_sqlite_url(project_root: Path) -> str:
    sqlite_path = (project_root / "data" / "portfoliomanager.db").resolve()
    return f"sqlite:///{sqlite_path.as_posix()}"


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    database_url: str
    secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    cookie_samesite: str
    cookie_secure: bool
    ocr_cmd: Optional[str]
    ocr_lang: str
    finnhub_key: Optional[str]
    alphavantage_key: Optional[str]
    brapi_token: Optional[str]
    twelvedata_key: Optional[str]
    fmp_key: Optional[str]
    admin_bootstrap_user: Optional[str]
    admin_bootstrap_pass: Optional[str]
    admin_bootstrap_email: Optional[str]
    data_dir: Path
    run_dir: Path
    log_dir: Path
    upload_dir: Path
    ocr_cache_dir: Path
    backup_dir: Path

    def ensure_runtime_dirs(self) -> None:
        """
        Cria diretórios operacionais se ausentes.
        Não cria/edita estrutura de código ou banco.
        """
        for path in (self.data_dir, self.run_dir, self.log_dir, self.upload_dir, self.ocr_cache_dir, self.backup_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    project_root = Path(__file__).resolve().parents[2]
    default_db_url = _default_sqlite_url(project_root)
    database_url = _normalize_database_url(os.getenv("DATABASE_URL", default_db_url))

    settings = AppSettings(
        project_root=project_root,
        database_url=database_url,
        secret_key=os.getenv("SECRET_KEY", "dev-only-secret-change-me"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        cookie_samesite=os.getenv("COOKIE_SAMESITE", "lax"),
        cookie_secure=_parse_bool(os.getenv("COOKIE_SECURE", "false"), default=False),
        ocr_cmd=os.getenv("OCR_CMD"),
        ocr_lang=os.getenv("OCR_LANG", "eng+por"),
        finnhub_key=os.getenv("FINNHUB_KEY"),
        alphavantage_key=os.getenv("ALPHAVANTAGE_KEY"),
        brapi_token=os.getenv("BRAPI_TOKEN"),
        twelvedata_key=os.getenv("TWELVEDATA_KEY"),
        fmp_key=os.getenv("FMP_KEY"),
        admin_bootstrap_user=os.getenv("ADMIN_BOOTSTRAP_USER"),
        admin_bootstrap_pass=os.getenv("ADMIN_BOOTSTRAP_PASS"),
        admin_bootstrap_email=os.getenv("ADMIN_BOOTSTRAP_EMAIL"),
        data_dir=(project_root / "data"),
        run_dir=(project_root / "var" / ".run"),
        log_dir=(project_root / "var" / "logs"),
        upload_dir=(project_root / "var" / "logs" / "uploads"),
        ocr_cache_dir=(project_root / "var" / "logs" / "ocr"),
        backup_dir=(project_root / "var" / "backups" / "postgres"),
    )
    settings.ensure_runtime_dirs()
    return settings

