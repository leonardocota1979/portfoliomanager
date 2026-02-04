#!/usr/bin/env python3
import sqlite3
import shutil
from datetime import datetime

print("="*60)
print("🔄 MIGRAÇÃO DE DADOS")
print("="*60)

# 1. PARA O SERVIDOR
print("\n⚠️  PARE O SERVIDOR (Ctrl+C) e pressione Enter aqui...")
input()

# 2. BACKUP
print("\n📦 Fazendo backup do banco antigo...")
shutil.copy("portfoliomanager.db", f"backups/pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
print("✅ Backup criado!")

# 3. CONECTA AO BANCO
conn = sqlite3.connect("portfoliomanager.db")
cursor = conn.cursor()

# 4. ADICIONA COLUNAS FALTANTES
print("\n🔨 Adicionando colunas novas...")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    print("  ✅ users.is_admin")
except sqlite3.OperationalError:
    print("  ⏭️  users.is_admin já existe")

try:
    cursor.execute("ALTER TABLE portfolios ADD COLUMN total_value REAL DEFAULT 0.0")
    print("  ✅ portfolios.total_value")
except sqlite3.OperationalError:
    print("  ⏭️  portfolios.total_value já existe")

try:
    cursor.execute("ALTER TABLE portfolios ADD COLUMN currency TEXT DEFAULT 'USD'")
    print("  ✅ portfolios.currency")
except sqlite3.OperationalError:
    print("  ⏭️  portfolios.currency já existe")

try:
    cursor.execute("ALTER TABLE asset_classes ADD COLUMN is_custom INTEGER DEFAULT 0")
    print("  ✅ asset_classes.is_custom")
except sqlite3.OperationalError:
    print("  ⏭️  asset_classes.is_custom já existe")

try:
    cursor.execute("ALTER TABLE asset_classes ADD COLUMN pending_approval INTEGER DEFAULT 0")
    print("  ✅ asset_classes.pending_approval")
except sqlite3.OperationalError:
    print("  ⏭️  asset_classes.pending_approval já existe")

try:
    cursor.execute("ALTER TABLE assets ADD COLUMN source TEXT DEFAULT 'manual'")
    print("  ✅ assets.source")
except sqlite3.OperationalError:
    print("  ⏭️  assets.source já existe")

conn.commit()

# 5. CRIA TABELA DE CLASSES GLOBAIS
print("\n🌍 Criando tabela de classes globais...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_asset_classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 6. POPULA CLASSES GLOBAIS
classes = [
    ("Stocks", "Equities/Shares - Ações de empresas"),
    ("Bonds", "Fixed Income - Títulos de renda fixa"),
    ("REITs", "Real Estate Investment Trusts - Fundos Imobiliários"),
    ("Crypto", "Cryptocurrencies - Criptomoedas e ativos digitais"),
    ("Commodities", "Raw materials - Ouro, prata, petróleo, etc"),
]

for name, desc in classes:
    try:
        cursor.execute("INSERT INTO global_asset_classes (name, description) VALUES (?, ?)", (name, desc))
        print(f"  ✅ {name}")
    except sqlite3.IntegrityError:
        print(f"  ⏭️  {name} já existe")

conn.commit()
conn.close()

print("\n" + "="*60)
print("✅ MIGRAÇÃO CONCLUÍDA!")
print("="*60)
print("\n📋 Agora você pode:")
print("  1. Reiniciar o servidor: ./start_server.sh")
print("  2. Fazer login no sistema")
print("  3. Criar portfolios com valor total!")
print("="*60)

