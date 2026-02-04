#!/usr/bin/env python3
"""
migrate_add_price_columns.py

Migração para adicionar colunas de preço ao banco de dados existente.

Novas colunas:
- assets.last_price (Float)
- assets.last_price_updated (DateTime)
- assets.price_source (String)
- portfolios.last_prices_updated (DateTime)

Autor: Assistente de IA
Data: 27 de janeiro de 2026
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

print("=" * 60)
print("🔄 MIGRAÇÃO: Adicionar colunas de preço")
print("=" * 60)

# Caminho do banco
DB_PATH = Path("portfoliomanager.db")

if not DB_PATH.exists():
    print("❌ Banco de dados não encontrado!")
    print("   Execute este script na raiz do projeto.")
    exit(1)

# 1. BACKUP
print("\n📦 Passo 1: Criando backup...")
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)
backup_name = f"pre_price_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
backup_path = backup_dir / backup_name
shutil.copy(DB_PATH, backup_path)
print(f"   ✅ Backup criado: {backup_path}")

# 2. CONECTAR E MIGRAR
print("\n🔨 Passo 2: Adicionando colunas...")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Colunas a adicionar
migrations = [
    # Tabela assets
    ("assets", "last_price", "REAL DEFAULT 0.0"),
    ("assets", "last_price_updated", "TIMESTAMP NULL"),
    ("assets", "price_source", "TEXT NULL"),
    # Tabela portfolios
    ("portfolios", "last_prices_updated", "TIMESTAMP NULL"),
]

for table, column, definition in migrations:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"   ✅ {table}.{column}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"   ⏭️  {table}.{column} (já existe)")
        else:
            print(f"   ❌ {table}.{column}: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ MIGRAÇÃO CONCLUÍDA!")
print("=" * 60)
print("""
📋 Mudanças aplicadas:
   • assets.last_price - Último preço conhecido
   • assets.last_price_updated - Data/hora da última atualização
   • assets.price_source - Fonte do preço (yahoo, brapi, coingecko)
   • portfolios.last_prices_updated - Timestamp da última atualização de preços

🔄 Próximos passos:
   1. Reinicie o servidor: uvicorn app.main:app --reload
   2. Abra o dashboard de um portfolio
   3. Clique em "Atualizar Preços" para buscar cotações
""")
print("=" * 60)
