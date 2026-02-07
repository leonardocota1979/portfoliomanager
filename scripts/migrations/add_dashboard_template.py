"""Adiciona coluna `dashboard_template` em `portfolios` (somente SQLite)."""

import os
import sqlite3
from pathlib import Path

try:
    from app.core.settings import get_settings
    DATABASE_URL = get_settings().database_url
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/portfoliomanager.db")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL.startswith("sqlite:///"):
    raise SystemExit("Este script atende apenas SQLite. Use migração SQLAlchemy para Postgres.")

DB_PATH = DATABASE_URL.replace("sqlite:///", "", 1)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if not column_exists(cur, "portfolios", "dashboard_template"):
        cur.execute("ALTER TABLE portfolios ADD COLUMN dashboard_template TEXT DEFAULT 'v1'")
        conn.commit()
        print("OK: coluna dashboard_template adicionada.")
    else:
        print("OK: coluna dashboard_template já existe.")
    conn.close()


if __name__ == "__main__":
    main()
