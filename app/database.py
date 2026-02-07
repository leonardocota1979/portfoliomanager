# app/database.py
"""
Camada de dados principal da aplicação.

Pontos importantes para operação:
- Usa `DATABASE_URL` do ambiente.
- Suporta SQLite (local) e Postgres (Render/produção).
- Cria automaticamente diretório do arquivo SQLite quando necessário.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from .core.settings import get_settings

SETTINGS = get_settings()
DATABASE_URL = SETTINGS.database_url
DB_SCHEMA = SETTINGS.normalized_db_schema

# SQLite: cria diretório local e aplica connect_args específicos.
connect_args = {}
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    from pathlib import Path
    db_dir = Path(db_path).parent
    if db_dir:
        db_dir.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql://"):
    # Postgres compartilhado: fixa search_path no schema da aplicação.
    connect_args = {"options": f"-csearch_path={DB_SCHEMA}"}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento com cascade delete
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    total_value = Column(Float, default=0.0)  # Valor DEFINIDO pelo usuário (não calculado)
    currency = Column(String, default="USD")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_prices_updated = Column(DateTime, nullable=True)  # Última atualização de preços
    dashboard_template = Column(String, default="v1")
    
    owner = relationship("User", back_populates="portfolios")
    
    # Relacionamentos com cascade delete
    portfolio_assets = relationship("PortfolioAsset", back_populates="portfolio", cascade="all, delete-orphan")
    asset_classes = relationship("AssetClass", back_populates="portfolio", cascade="all, delete-orphan")


class GlobalAssetClass(Base):
    __tablename__ = "global_asset_classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssetClass(Base):
    __tablename__ = "asset_classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_percentage = Column(Float, default=0.0)  # % meta da classe no portfolio
    rebalance_threshold_percentage = Column(Float, default=5.0)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    is_custom = Column(Boolean, default=False)
    pending_approval = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="asset_classes")
    
    # Relacionamento com cascade delete
    assets = relationship("Asset", back_populates="asset_class", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("name", "portfolio_id", name="_asset_class_portfolio_uc"),
    )


class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    asset_class_id = Column(Integer, ForeignKey("asset_classes.id"), nullable=False)
    source = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Campos de preço (NOVOS)
    last_price = Column(Float, default=0.0)  # Último preço conhecido
    last_price_updated = Column(DateTime, nullable=True)  # Quando foi atualizado
    price_source = Column(String, nullable=True)  # Fonte do preço (Finnhub, Brapi, CoinGecko, manual)
    
    asset_class = relationship("AssetClass", back_populates="assets")
    
    # Relacionamento com cascade delete
    portfolio_assets = relationship("PortfolioAsset", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("ticker", "asset_class_id", name="_asset_ticker_class_uc"),
    )


class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    target_percentage = Column(Float, default=0.0)  # % meta do ativo DENTRO da classe
    rebalance_threshold_percentage = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="portfolio_assets")
    asset = relationship("Asset", back_populates="portfolio_assets")
    
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="_portfolio_asset_uc"),
    )


class AssetClassMapping(Base):
    __tablename__ = "asset_class_mappings"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    class_name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "class_name", name="_asset_class_mapping_uc"),
    )


def create_db_and_tables():
    """
    Cria/valida estrutura de banco.

    Comportamento:
    - SQLite: apenas cria tabelas.
    - Postgres: cria schema alvo, valida schema ativo (se enforce) e cria tabelas.
    """
    if DATABASE_URL.startswith("postgresql://"):
        _ensure_postgres_schema_ready()
    Base.metadata.create_all(bind=engine)


def _ensure_postgres_schema_ready():
    """
    Garante isolamento por schema no Postgres compartilhado.

    Passos:
    1) CREATE SCHEMA IF NOT EXISTS <schema>
    2) SET search_path para o schema do projeto
    3) validar current_schema()
    """
    schema = DB_SCHEMA
    quoted_schema = f'"{schema}"'

    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}"))
        connection.execute(text(f"SET search_path TO {quoted_schema}"))
        active_schema = connection.execute(text("SELECT current_schema()")).scalar()

        if SETTINGS.enforce_db_schema and active_schema != schema:
            raise RuntimeError(
                "Schema ativo divergente. "
                f"Esperado='{schema}' Atual='{active_schema}'. "
                "Revise DATABASE_URL/DB_SCHEMA/ENFORCE_DB_SCHEMA."
            )


def get_db():
    """Generator para obter sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
