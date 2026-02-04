"""Adiciona coluna dashboard_template em portfolios (SQLite)."""

import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./portfoliomanager.db")

if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")


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
