#!/usr/bin/env python3
# scripts/create_admin.py
"""
Cria ou promove um usuário admin.

Uso:
  python scripts/create_admin.py --username admin --password senha123 --email admin@local
  python scripts/create_admin.py --username admin --make-admin-only
"""

import argparse
import os
import sys

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.database import SessionLocal, User
from app import crud


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cria ou promove um usuário admin.")
    parser.add_argument("--username", required=True, help="Username do usuário")
    parser.add_argument("--password", help="Senha (obrigatório para criar usuário)")
    parser.add_argument("--email", default=None, help="Email do usuário")
    parser.add_argument(
        "--make-admin-only",
        action="store_true",
        help="Apenas promove para admin (não altera senha)"
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    db = SessionLocal()
    try:
        user = crud.get_user_by_username(db, args.username)

        if user:
            user.is_admin = True
            if not args.make_admin_only and args.password:
                user.hashed_password = crud.get_password_hash(args.password)
            db.commit()
            print(f"OK: Usuário '{args.username}' promovido para admin.")
            return

        if args.make_admin_only:
            print("ERRO: usuário não existe e --make-admin-only foi usado.")
            return

        if not args.password:
            print("ERRO: --password é obrigatório para criar usuário.")
            return

        new_user = User(
            username=args.username,
            email=args.email,
            hashed_password=crud.get_password_hash(args.password),
            is_admin=True
        )
        db.add(new_user)
        db.commit()
        print(f"OK: Admin '{args.username}' criado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
