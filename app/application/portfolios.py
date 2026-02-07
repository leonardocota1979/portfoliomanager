"""
Casos de uso de Portfólios.

Motivação:
- manter regras de negócio fora dos routers;
- facilitar manutenção e testes sem tocar em HTTP/template.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import Portfolio as PortfolioModel, User as UserModel
from ..dependencies import verify_portfolio_ownership


class PortfolioUseCases:
    """Orquestra operações de portfólio para uso nos endpoints."""

    def list_by_user(self, db: Session, user: UserModel, skip: int = 0, limit: int = 100):
        return crud.get_portfolios_by_user(db, user_id=user.id, skip=skip, limit=limit)

    def create(self, db: Session, user: UserModel, payload: schemas.PortfolioCreate) -> PortfolioModel:
        return crud.create_portfolio(db=db, portfolio=payload, user_id=user.id)

    def get_owned(self, db: Session, user: UserModel, portfolio_id: int) -> PortfolioModel:
        return verify_portfolio_ownership(portfolio_id, user, db)

    def update_owned(self, db: Session, user: UserModel, portfolio_id: int, payload: schemas.PortfolioCreate) -> PortfolioModel:
        portfolio = self.get_owned(db, user, portfolio_id)
        portfolio.name = payload.name
        portfolio.description = payload.description
        portfolio.total_value = payload.total_value
        portfolio.currency = payload.currency
        db.commit()
        db.refresh(portfolio)
        return portfolio

    def delete_owned(self, db: Session, user: UserModel, portfolio_id: int) -> None:
        portfolio = self.get_owned(db, user, portfolio_id)
        db.delete(portfolio)
        db.commit()

