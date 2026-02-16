#!/usr/bin/env python3
"""
Migra dados do SQLite local para PostgreSQL (Render), preservando IDs.

Uso:
  source venv/bin/activate
  python scripts/maintenance/migrate_sqlite_to_postgres.py \
    --sqlite data/portfoliomanager.db \
    --postgres-url "postgresql://..." \
    --schema portfolio_manager \
    --truncate

Observações:
- O schema de destino é garantido automaticamente.
- As tabelas são criadas no Postgres, se não existirem.
- Quando --truncate é usado, os dados antigos do schema são removidos antes da carga.
- Ao final, o script valida contagem SQLite vs Postgres por tabela.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Garante import do pacote `app` ao executar como script direto.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importa apenas metadados dos modelos para criar estrutura no Postgres.
from app.database import Base


TABLE_ORDER: List[str] = [
    "users",
    "global_asset_classes",
    "portfolios",
    "asset_classes",
    "assets",
    "portfolio_assets",
    "asset_class_mappings",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migra SQLite local para Postgres")
    parser.add_argument(
        "--sqlite",
        default="data/portfoliomanager.db",
        help="Caminho do banco SQLite local",
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="URL do Postgres de destino (Internal Database URL do Render)",
    )
    parser.add_argument(
        "--schema",
        default="portfolio_manager",
        help="Schema de destino no Postgres",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Limpa tabelas de destino antes da carga",
    )
    return parser.parse_args()


def build_engines(sqlite_path: Path, postgres_url: str, schema: str) -> tuple[Engine, Engine]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite não encontrado: {sqlite_path}")
    if not postgres_url.startswith("postgresql://"):
        raise ValueError("Use URL iniciando com 'postgresql://'.")

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path.resolve().as_posix()}")
    postgres_engine = create_engine(
        postgres_url,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    return sqlite_engine, postgres_engine


def ensure_schema_and_tables(postgres_engine: Engine, schema: str) -> None:
    quoted_schema = f'"{schema}"'
    with postgres_engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}"))
        connection.execute(text(f"SET search_path TO {quoted_schema}"))
    Base.metadata.create_all(bind=postgres_engine)


def fetch_rows(sqlite_engine: Engine, table_name: str) -> List[dict]:
    with sqlite_engine.connect() as connection:
        result = connection.execute(text(f'SELECT * FROM "{table_name}"'))
        return [dict(row) for row in result.mappings().all()]


def truncate_tables(postgres_engine: Engine) -> None:
    with postgres_engine.begin() as connection:
        for table_name in reversed(TABLE_ORDER):
            connection.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))


def insert_rows(postgres_engine: Engine, table_name: str, rows: List[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    col_sql = ", ".join(f'"{col}"' for col in columns)
    val_sql = ", ".join(f":{col}" for col in columns)
    stmt = text(f'INSERT INTO "{table_name}" ({col_sql}) VALUES ({val_sql})')
    with postgres_engine.begin() as connection:
        connection.execute(stmt, rows)


def reset_sequences(postgres_engine: Engine) -> None:
    with postgres_engine.begin() as connection:
        for table_name in TABLE_ORDER:
            connection.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('"{table_name}"', 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table_name}"), 1),
                        true
                    )
                    """
                )
            )


def count_rows(engine: Engine, table_name: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0)


def validate_counts(sqlite_engine: Engine, postgres_engine: Engine) -> Dict[str, tuple[int, int]]:
    summary: Dict[str, tuple[int, int]] = {}
    for table_name in TABLE_ORDER:
        src = count_rows(sqlite_engine, table_name)
        dst = count_rows(postgres_engine, table_name)
        summary[table_name] = (src, dst)
    return summary


def main() -> int:
    args = parse_args()
    sqlite_path = Path(args.sqlite)
    schema = args.schema.strip()

    try:
        sqlite_engine, postgres_engine = build_engines(sqlite_path, args.postgres_url, schema)
        ensure_schema_and_tables(postgres_engine, schema)

        if args.truncate:
            truncate_tables(postgres_engine)

        for table_name in TABLE_ORDER:
            rows = fetch_rows(sqlite_engine, table_name)
            insert_rows(postgres_engine, table_name, rows)
            print(f"{table_name}: inseridos {len(rows)} registros")

        reset_sequences(postgres_engine)
        summary = validate_counts(sqlite_engine, postgres_engine)

        has_mismatch = False
        print("\nResumo de validação (SQLite -> Postgres):")
        for table_name, (src, dst) in summary.items():
            marker = "OK" if src == dst else "DIVERGENTE"
            print(f"- {table_name}: {src} -> {dst} [{marker}]")
            if src != dst:
                has_mismatch = True

        if has_mismatch:
            print("\nMigração concluída com divergência de contagem.")
            return 2

        print("\nMigração concluída com sucesso.")
        return 0
    except (SQLAlchemyError, OSError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
