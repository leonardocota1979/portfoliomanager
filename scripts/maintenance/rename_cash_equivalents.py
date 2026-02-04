#!/usr/bin/env python3
# scripts/maintenance/rename_cash_equivalents.py
"""
Renomeia classes "Cash Equivalents" para "Reserva de Valor".
"""

from app.database import SessionLocal, AssetClass, GlobalAssetClass


def main() -> None:
    db = SessionLocal()
    try:
        updated = 0
        for cls in db.query(AssetClass).filter(AssetClass.name == "Cash Equivalents").all():
            cls.name = "Reserva de Valor"
            updated += 1
        for cls in db.query(GlobalAssetClass).filter(GlobalAssetClass.name == "Cash Equivalents").all():
            cls.name = "Reserva de Valor"
            updated += 1
        db.commit()
        print(f"OK: renomeados {updated} registros.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
