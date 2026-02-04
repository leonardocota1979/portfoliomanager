#!/usr/bin/env python3
# scripts/migrate_asset_target_to_class.py
"""
Migra % meta dos ativos do portfólio para % meta dentro da classe.

Regra:
  novo_pct_classe = (pct_portfolio_antigo / pct_classe) * 100

Exemplo:
  Classe = 15% do portfólio
  Ativo = 7.5% do portfólio
  Novo % na classe = (7.5 / 15) * 100 = 50%
"""

import argparse
import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.database import SessionLocal, PortfolioAsset, Asset, AssetClass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra % meta de ativos para % dentro da classe."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não grava mudanças, apenas mostra o que seria feito."
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    db = SessionLocal()
    try:
        portfolio_assets = (
            db.query(PortfolioAsset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .join(AssetClass, Asset.asset_class_id == AssetClass.id)
            .all()
        )

        updated = 0
        skipped = 0

        for pa in portfolio_assets:
            asset = db.query(Asset).filter(Asset.id == pa.asset_id).first()
            if not asset:
                skipped += 1
                continue

            asset_class = db.query(AssetClass).filter(AssetClass.id == asset.asset_class_id).first()
            if not asset_class:
                skipped += 1
                continue

            class_pct = asset_class.target_percentage or 0.0
            old_pct = pa.target_percentage or 0.0

            if class_pct <= 0:
                skipped += 1
                continue

            new_pct = (old_pct / class_pct) * 100.0

            if not args.dry_run:
                pa.target_percentage = new_pct
            updated += 1

        if not args.dry_run:
            db.commit()

        mode = "DRY-RUN" if args.dry_run else "APLICADO"
        print(f"{mode}: atualizados={updated}, ignorados={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
