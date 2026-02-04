#!/usr/bin/env python3
"""
Script de Migração: Adiciona colunas de preço ao banco de dados

Executa: python scripts/migrate_add_price_columns.py

Novas colunas:
- Asset: last_price, last_price_updated, price_source
- Portfolio: last_prices_updated
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path


def migrate():
    db_path = Path("portfoliomanager.db")
    
    if not db_path.exists():
        print("❌ Banco de dados não encontrado: portfoliomanager.db")
        print("   Execute o servidor primeiro para criar o banco.")
        return False
    
    # Backup
    backup_path = db_path.with_suffix(f".db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    print(f"📦 Criando backup: {backup_path}")
    shutil.copy(db_path, backup_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    migrations = [
        # Asset columns
        ("assets", "last_price", "FLOAT DEFAULT 0.0"),
        ("assets", "last_price_updated", "DATETIME"),
        ("assets", "price_source", "VARCHAR"),
        
        # Portfolio columns
        ("portfolios", "last_prices_updated", "DATETIME"),
    ]
    
    for table, column, col_type in migrations:
        try:
            # Verifica se coluna já existe
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if column in columns:
                print(f"⏭️  Coluna {table}.{column} já existe")
            else:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"✅ Adicionada coluna {table}.{column}")
                
        except Exception as e:
            print(f"❌ Erro ao adicionar {table}.{column}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migração concluída!")
    print(f"   Backup salvo em: {backup_path}")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("MIGRAÇÃO: Adicionar colunas de preço")
    print("=" * 50)
    migrate()
