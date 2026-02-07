# app/routers/portfolios.py
"""
Router de Portfolios - VERSÃO CORRIGIDA

Correções:
- PUT atualiza total_value e currency
- Botões de Editar e Deletar funcionando
"""

from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db, User as UserModel
from ..dependencies import get_current_active_user
from ..application.portfolios import PortfolioUseCases

router = APIRouter(
    tags=["Portfolios"]
)
portfolio_use_cases = PortfolioUseCases()


@router.get("/list", response_class=HTMLResponse)
async def list_portfolios_page(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Renderiza a página HTML que lista as carteiras."""
    from ..main import templates
    portfolios = portfolio_use_cases.list_by_user(db=db, user=current_user)
    return templates.TemplateResponse(
        "portfolio_list.html",
        {
            "request": request,
            "title": "Minhas Carteiras",
            "portfolios": portfolios,
            "current_user": current_user
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_portfolio_page(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Renderiza página de criar portfolio."""
    from ..main import templates
    return templates.TemplateResponse(
        "portfolio_create.html",
        {"request": request, "title": "Criar Carteira", "current_user": current_user}
    )


@router.get("/setup", response_class=HTMLResponse)
async def setup_portfolio_page(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Renderiza página de setup completo do portfolio."""
    from ..main import templates
    return templates.TemplateResponse(
        "portfolio_setup.html",
        {"request": request, "title": "Configurar Portfólio", "current_user": current_user}
    )


@router.post("/", response_model=schemas.Portfolio)
def create_portfolio(
    portfolio: schemas.PortfolioCreate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Cria um novo portfolio."""
    return portfolio_use_cases.create(db=db, user=current_user, payload=portfolio)


@router.get("/", response_model=List[schemas.Portfolio])
def read_portfolios(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista todos os portfolios do usuário."""
    portfolios = portfolio_use_cases.list_by_user(db=db, user=current_user, skip=skip, limit=limit)
    return portfolios


@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
def read_portfolio(
    portfolio_id: int,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Busca um portfolio específico."""
    portfolio = portfolio_use_cases.get_owned(db=db, user=current_user, portfolio_id=portfolio_id)
    return portfolio


@router.put("/{portfolio_id}", response_model=schemas.Portfolio)
def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioCreate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Atualiza um portfolio existente.
    
    IMPORTANTE: Atualiza TODOS os campos incluindo:
    - name
    - description  
    - total_value (valor definido pelo usuário)
    - currency
    """
    return portfolio_use_cases.update_owned(
        db=db,
        user=current_user,
        portfolio_id=portfolio_id,
        payload=portfolio
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Deleta um portfolio e todos os dados relacionados (cascade)."""
    portfolio_use_cases.delete_owned(db=db, user=current_user, portfolio_id=portfolio_id)
    return None
