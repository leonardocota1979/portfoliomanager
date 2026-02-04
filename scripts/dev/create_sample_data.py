#!/usr/bin/env python3

print("="*60)
print("🎲 CRIANDO DADOS DE EXEMPLO")
print("="*60)

from app.database import SessionLocal, Portfolio, AssetClass, Asset, PortfolioAsset
from app import crud

db = SessionLocal()

# Busca o portfolio que você criou
portfolio = db.query(Portfolio).filter(Portfolio.name.like("%Convex%")).first()

if not portfolio:
    print("❌ Portfolio não encontrado! Crie um primeiro.")
    db.close()
    exit()

print(f"\n📂 Portfolio: {portfolio.name}")
print(f"💰 Valor Total: ${portfolio.total_value:,.2f}")

# Busca as classes do portfolio
classes = db.query(AssetClass).filter(AssetClass.portfolio_id == portfolio.id).all()

print(f"\n📊 Classes configuradas: {len(classes)}")
for cls in classes:
    print(f"  • {cls.name}: {cls.target_percentage}%")

# CRIAR ATIVOS DE EXEMPLO
print("\n🔨 Criando ativos de exemplo...")

ativos_exemplo = [
    # Stocks (30%)
    {"name": "Apple Inc.", "ticker": "AAPL", "class_name": "Stocks", "percentage": 10.0, "price": 175.43},
    {"name": "Microsoft Corp.", "ticker": "MSFT", "class_name": "Stocks", "percentage": 10.0, "price": 378.91},
    {"name": "Alphabet Inc.", "ticker": "GOOGL", "class_name": "Stocks", "percentage": 10.0, "price": 141.80},
    
    # Bonds (20%)
    {"name": "iShares Core US Aggregate Bond ETF", "ticker": "AGG", "class_name": "Bonds", "percentage": 20.0, "price": 98.50},
    
    # REITs (15%)
    {"name": "Vanguard Real Estate ETF", "ticker": "VNQ", "class_name": "REITs", "percentage": 15.0, "price": 88.32},
    
    # Crypto (10%)
    {"name": "Bitcoin", "ticker": "BTC-USD", "class_name": "Crypto", "percentage": 10.0, "price": 98500.00},
    
    # Commodities (10%)
    {"name": "SPDR Gold Shares", "ticker": "GLD", "class_name": "Commodities", "percentage": 10.0, "price": 234.56},
    
    # Reserva de Valor (15%)
    {"name": "Tesouro Selic 2026", "ticker": "SELIC-2026", "class_name": "Reserva de Valor", "percentage": 15.0, "price": 1.00},
]

for ativo_data in ativos_exemplo:
    # Busca a classe
    classe = next((c for c in classes if c.name == ativo_data["class_name"]), None)
    
    if not classe:
        print(f"  ⏭️  Classe '{ativo_data['class_name']}' não encontrada no portfolio")
        continue
    
    # Verifica se o asset já existe globalmente
    existing_asset = db.query(Asset).filter(Asset.ticker == ativo_data["ticker"]).first()
    
    if not existing_asset:
        # Cria o asset
        asset = Asset(
            name=ativo_data["name"],
            ticker=ativo_data["ticker"],
            asset_class_id=classe.id,
            source="manual"
        )
        db.add(asset)
        db.flush()
    else:
        asset = existing_asset
    
    # Verifica se já está no portfolio
    existing_pa = db.query(PortfolioAsset).filter(
        PortfolioAsset.portfolio_id == portfolio.id,
        PortfolioAsset.asset_id == asset.id
    ).first()
    
    if not existing_pa:
        # Calcula quantidade baseada no percentual e preço
        target_value = (ativo_data["percentage"] / 100) * portfolio.total_value
        quantity = target_value / ativo_data["price"] if ativo_data["price"] > 0 else 0
        
        # Adiciona ao portfolio
        pa = PortfolioAsset(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=quantity,
            target_percentage=ativo_data["percentage"],
            rebalance_threshold_percentage=5.0
        )
        db.add(pa)
        print(f"  ✅ {ativo_data['ticker']} - {quantity:.4f} unidades (${target_value:,.2f})")
    else:
        print(f"  ⏭️  {ativo_data['ticker']} já está no portfolio")

db.commit()

print("\n" + "="*60)
print("✅ DADOS DE EXEMPLO CRIADOS!")
print("="*60)
print("\n📋 Agora você pode:")
print("  1. Ir para /dashboard/?portfolio_id=" + str(portfolio.id))
print("  2. Ver os ativos com valores reais")
print("  3. Ver status de rebalanceamento")
print("="*60)

db.close()
