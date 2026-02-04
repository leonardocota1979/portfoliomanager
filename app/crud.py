# app/crud.py
# Funções CRUD para interagir com o banco de dados

from sqlalchemy.orm import Session
from . import database as models
from . import schemas
from passlib.context import CryptContext
from typing import Optional, List

# --- Configuração de Hash de Senha ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Gera hash bcrypt de uma senha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ==============================================================================
# CRUD - USUÁRIOS
# ==============================================================================

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Busca usuário por ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Busca usuário por username"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Lista todos os usuários com paginação"""
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Cria novo usuário com senha hasheada"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_admin=getattr(user, "is_admin", False)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: models.User, data: schemas.UserUpdate) -> models.User:
    """Atualiza dados básicos do usuário."""
    if data.username is not None:
        user.username = data.username
    if data.email is not None:
        user.email = data.email
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    db.commit()
    db.refresh(user)
    return user

def set_user_password(db: Session, user: models.User, password: str) -> models.User:
    """Atualiza a senha do usuário."""
    user.hashed_password = get_password_hash(password)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: models.User) -> None:
    """Remove usuário e dados relacionados (cascade)."""
    db.delete(user)
    db.commit()

# ==============================================================================
# CRUD - PORTFOLIOS
# ==============================================================================

def get_portfolio(db: Session, portfolio_id: int) -> Optional[models.Portfolio]:
    """Busca portfolio por ID"""
    return db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id
    ).first()

def get_portfolios_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Portfolio]:
    """Lista portfolios de um usuário específico"""
    return db.query(models.Portfolio).filter(
        models.Portfolio.owner_id == user_id
    ).offset(skip).limit(limit).all()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate, user_id: int) -> models.Portfolio:
    """Cria novo portfolio para um usuário"""
    db_portfolio = models.Portfolio(
        name=portfolio.name,
        description=portfolio.description,
        # CORREÇÃO: Agora salva total_value e currency
        total_value=portfolio.total_value,
        currency=portfolio.currency,
        owner_id=user_id
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

# ==============================================================================
# CRUD - ASSET CLASSES
# ==============================================================================

def get_asset_class(db: Session, asset_class_id: int) -> Optional[models.AssetClass]:
    """Busca classe de ativo por ID"""
    return db.query(models.AssetClass).filter(
        models.AssetClass.id == asset_class_id
    ).first()

def get_asset_classes_by_portfolio(db: Session, portfolio_id: int) -> List[models.AssetClass]:
    """Lista classes de ativos de um portfolio"""
    return db.query(models.AssetClass).filter(
        models.AssetClass.portfolio_id == portfolio_id
    ).all()

def create_asset_class(db: Session, asset_class: schemas.AssetClassCreate, portfolio_id: int) -> models.AssetClass:
    """Cria nova classe de ativo em um portfolio"""
    db_asset_class = models.AssetClass(
        name=asset_class.name,
        target_percentage=asset_class.target_percentage,
        rebalance_threshold_percentage=asset_class.rebalance_threshold_percentage,
        portfolio_id=portfolio_id
    )
    db.add(db_asset_class)
    db.commit()
    db.refresh(db_asset_class)
    return db_asset_class

# ==============================================================================
# CRUD - ASSETS
# ==============================================================================

def get_asset(db: Session, asset_id: int) -> Optional[models.Asset]:
    """Busca ativo por ID"""
    return db.query(models.Asset).filter(models.Asset.id == asset_id).first()

def get_asset_by_ticker(db: Session, ticker: str) -> Optional[models.Asset]:
    """Busca ativo por ticker (ex: AAPL, BTC-USD)"""
    return db.query(models.Asset).filter(models.Asset.ticker == ticker).first()

def get_asset_by_ticker_and_class(db: Session, ticker: str, asset_class_id: int) -> Optional[models.Asset]:
    """Busca ativo por ticker + classe"""
    return db.query(models.Asset).filter(
        models.Asset.ticker == ticker,
        models.Asset.asset_class_id == asset_class_id
    ).first()

def get_assets_by_class(db: Session, asset_class_id: int) -> List[models.Asset]:
    """Lista ativos de uma classe específica"""
    return db.query(models.Asset).filter(
        models.Asset.asset_class_id == asset_class_id
    ).all()

def create_asset(db: Session, asset: schemas.AssetCreate) -> models.Asset:
    """Cria novo ativo"""
    db_asset = models.Asset(
        name=asset.name,
        ticker=asset.ticker,
        asset_class_id=asset.asset_class_id
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

# ==============================================================================
# CRUD - PORTFOLIO ASSETS (Ativos na Carteira)
# ==============================================================================

def get_portfolio_asset(db: Session, portfolio_asset_id: int) -> Optional[models.PortfolioAsset]:
    """Busca um ativo específico de uma carteira por ID"""
    return db.query(models.PortfolioAsset).filter(
        models.PortfolioAsset.id == portfolio_asset_id
    ).first()

def get_portfolio_assets_by_portfolio(db: Session, portfolio_id: int) -> List[models.PortfolioAsset]:
    """Lista todos os ativos de uma carteira"""
    return db.query(models.PortfolioAsset).filter(
        models.PortfolioAsset.portfolio_id == portfolio_id
    ).all()

def create_portfolio_asset(db: Session, portfolio_asset: schemas.PortfolioAssetCreate, portfolio_id: int) -> models.PortfolioAsset:
    """Adiciona um ativo a uma carteira"""
    db_portfolio_asset = models.PortfolioAsset(
        portfolio_id=portfolio_id,
        asset_id=portfolio_asset.asset_id,
        quantity=portfolio_asset.quantity,
        target_percentage=portfolio_asset.target_percentage,
        rebalance_threshold_percentage=portfolio_asset.rebalance_threshold_percentage
    )
    db.add(db_portfolio_asset)
    db.commit()
    db.refresh(db_portfolio_asset)
    return db_portfolio_asset

def update_portfolio_asset_quantity(db: Session, portfolio_asset_id: int, new_quantity: float) -> Optional[models.PortfolioAsset]:
    """Atualiza a quantidade de um ativo na carteira"""
    db_portfolio_asset = get_portfolio_asset(db, portfolio_asset_id)
    if db_portfolio_asset:
        db_portfolio_asset.quantity = new_quantity
        db.commit()
        db.refresh(db_portfolio_asset)
    return db_portfolio_asset
