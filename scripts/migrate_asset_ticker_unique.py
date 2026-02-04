#!/usr/bin/env python3
# scripts/migrate_asset_ticker_unique.py
"""
Migração SQLite:
- Remove UNIQUE em assets.ticker
- Adiciona UNIQUE (ticker, asset_class_id)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("portfoliomanager.db")


def main() -> None:
    if not DB_PATH.exists():
        print("Banco não encontrado.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")
        cur.execute("BEGIN;")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS assets_new (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            ticker VARCHAR NOT NULL,
            asset_class_id INTEGER NOT NULL,
            source VARCHAR,
            created_at DATETIME,
            last_price FLOAT,
            last_price_updated DATETIME,
            price_source VARCHAR,
            FOREIGN KEY(asset_class_id) REFERENCES asset_classes(id)
        );
        """)

        cur.execute("""
        INSERT INTO assets_new (id, name, ticker, asset_class_id, source, created_at, last_price, last_price_updated, price_source)
        SELECT id, name, ticker, asset_class_id, source, created_at, last_price, last_price_updated, price_source
        FROM assets;
        """)

        cur.execute("DROP TABLE assets;")
        cur.execute("ALTER TABLE assets_new RENAME TO assets;")

        cur.execute("CREATE INDEX IF NOT EXISTS ix_assets_ticker ON assets (ticker);")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS _asset_ticker_class_uc ON assets (ticker, asset_class_id);")

        cur.execute("COMMIT;")
        cur.execute("PRAGMA foreign_keys=ON;")
        print("OK: Migração aplicada.")
    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"ERRO: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
