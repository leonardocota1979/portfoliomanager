#!/usr/bin/env python3

print("🔧 Atualizando classes globais...\n")

from app.database import SessionLocal, GlobalAssetClass

db = SessionLocal()

# Remove classes antigas
print("🗑️  Removendo classes antigas...")
db.query(GlobalAssetClass).delete()
db.commit()

# Adiciona classes corretas
classes_corretas = [
    {"name": "Stocks", "description": "Equities/Shares - Ações de empresas"},
    {"name": "Bonds", "description": "Fixed Income - Títulos de renda fixa"},
    {"name": "REITs", "description": "Real Estate Investment Trusts - Fundos Imobiliários"},
    {"name": "Crypto", "description": "Cryptocurrencies - Criptomoedas e ativos digitais"},
    {"name": "Commodities", "description": "Raw materials - Ouro, prata, petróleo, etc"},
]

print("✅ Criando classes corretas:")
for classe_data in classes_corretas:
    classe = GlobalAssetClass(**classe_data)
    db.add(classe)
    print(f"  • {classe_data['name']} - {classe_data['description']}")

db.commit()
db.close()

print("\n✅ Classes globais atualizadas!")
print("\n📝 NOTA: ETFs não são classe, são instrumentos de acesso")
print("   Exemplo: ETF de Bitcoin vai na classe 'Crypto'")
print("           ETF de Ouro vai na classe 'Commodities'")

