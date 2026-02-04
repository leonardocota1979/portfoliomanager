#!/usr/bin/env python3
import shutil
from datetime import datetime
from pathlib import Path

print("="*60)
print("🔧 UPGRADE DO BANCO DE DADOS - Portfolio Manager")
print("="*60)

# 1. BACKUP
print("\n📦 Passo 1: Fazendo backup do banco...")
db_file = Path("portfoliomanager.db")
if db_file.exists():
    backup_name = f"portfoliomanager_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(db_file, f"backups/{backup_name}")
    print(f"✅ Backup criado: backups/{backup_name}")
else:
    print("⚠️  Banco de dados não encontrado, será criado do zero")

# 2. ATUALIZAR MODELOS
print("\n🔨 Passo 2: Atualizando modelos...")

database_code = '''from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./portfoliomanager.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
    portfolios = relationship("Portfolio", back_populates="owner")

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    total_value = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="portfolios")
    portfolio_assets = relationship("PortfolioAsset", back_populates="portfolio")
    asset_classes = relationship("AssetClass", back_populates="portfolio")

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
    target_percentage = Column(Float, default=0.0)
    rebalance_threshold_percentage = Column(Float, default=5.0)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    is_custom = Column(Boolean, default=False)
    pending_approval = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    portfolio = relationship("Portfolio", back_populates="asset_classes")
    assets = relationship("Asset", back_populates="asset_class")
    __table_args__ = (UniqueConstraint("name", "portfolio_id", name="_asset_class_portfolio_uc"),)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ticker = Column(String, unique=True, index=True, nullable=False)
    asset_class_id = Column(Integer, ForeignKey("asset_classes.id"), nullable=False)
    source = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)
    asset_class = relationship("AssetClass", back_populates="assets")
    portfolio_assets = relationship("PortfolioAsset", back_populates="asset")

class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    target_percentage = Column(Float, default=0.0)
    rebalance_threshold_percentage = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    portfolio = relationship("Portfolio", back_populates="portfolio_assets")
    asset = relationship("Asset", back_populates="portfolio_assets")
    __table_args__ = (UniqueConstraint("portfolio_id", "asset_id", name="_portfolio_asset_uc"),)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

with open('app/database.py', 'w') as f:
    f.write(database_code)

print("✅ Arquivo database.py atualizado")

# 3. RECRIAR TABELAS
print("\n🔄 Passo 3: Recriando tabelas...")
from app.database import create_db_and_tables
create_db_and_tables()
print("✅ Tabelas criadas/atualizadas")

# 4. POPULAR CLASSES GLOBAIS
print("\n🌍 Passo 4: Criando classes globais padrão...")
from app.database import SessionLocal, GlobalAssetClass

db = SessionLocal()

classes_padrao = [
    {"name": "Ações", "description": "Ações de empresas (stocks)"},
    {"name": "Renda Fixa", "description": "Títulos de renda fixa"},
    {"name": "FIIs", "description": "Fundos Imobiliários"},
    {"name": "Criptomoedas", "description": "Ativos digitais (crypto)"},
    {"name": "ETFs", "description": "Exchange Traded Funds"},
    {"name": "Commodities", "description": "Ouro, prata, petróleo, etc"},
]

for classe_data in classes_padrao:
    existing = db.query(GlobalAssetClass).filter(
        GlobalAssetClass.name == classe_data["name"]
    ).first()
    
    if not existing:
        classe = GlobalAssetClass(**classe_data)
        db.add(classe)
        print(f"  ✅ {classe_data['name']}")
    else:
        print(f"  ⏭️  {classe_data['name']} (já existe)")

db.commit()
db.close()

print("\n" + "="*60)
print("✅ UPGRADE CONCLUÍDO COM SUCESSO!")
print("="*60)
print("\n📋 MUDANÇAS:")
print("  • Campo 'total_value' adicionado aos portfolios")
print("  • Campo 'currency' adicionado aos portfolios")
print("  • Campo 'is_admin' adicionado aos users")
print("  • Tabela 'global_asset_classes' criada")
print("  • 6 classes globais criadas")
print("  • Sistema de aprovação de classes customizadas")
print("\n🔄 O servidor vai recarregar automaticamente")
print("="*60)

