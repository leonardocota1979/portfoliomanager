#!/usr/bin/env python3
"""
Upgrade seguro de banco para ambiente local.

Objetivo:
- Criar tabelas ausentes com base nos models atuais.
- Garantir classes globais padrão.
- Não sobrescrever nenhum arquivo do projeto.
"""

from app.database import SessionLocal, create_db_and_tables, GlobalAssetClass


def ensure_global_asset_classes() -> None:
    defaults = [
        ("Stocks", "Equities/Shares - Ações de empresas"),
        ("Bonds", "Fixed Income - Títulos de renda fixa"),
        ("REITs", "Real Estate Investment Trusts - Fundos Imobiliários"),
        ("Crypto", "Cryptocurrencies - Criptomoedas e ativos digitais"),
        ("Commodities", "Raw materials - Ouro, prata, petróleo, etc"),
        ("Reserva de Valor", "Reserva de valor - Caixa e equivalentes"),
    ]
    db = SessionLocal()
    try:
        existing = {row.name for row in db.query(GlobalAssetClass).all()}
        for name, desc in defaults:
            if name in existing:
                continue
            db.add(GlobalAssetClass(name=name, description=desc))
        db.commit()
    finally:
        db.close()


def main() -> None:
    print("Iniciando upgrade seguro do banco...")
    create_db_and_tables()
    ensure_global_asset_classes()
    print("Upgrade concluido com sucesso.")


if __name__ == "__main__":
    main()
