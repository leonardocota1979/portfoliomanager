# app/database.py
"""
Modelos do Banco de Dados - VERSÃO ATUALIZADA

Mudanças:
- Adicionado campos de preço em Asset (last_price, last_price_updated, price_source)
- Adicionado last_prices_updated em Portfolio
- Cascade delete em todos os relacionamentos
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/portfoliomanager.db")

# SQLite: ensure directory exists and set connect_args
connect_args = {}
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    connect_args = {"check_same_thread": False}

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
    """Cria todas as tabelas no banco de dados."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Generator para obter sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
