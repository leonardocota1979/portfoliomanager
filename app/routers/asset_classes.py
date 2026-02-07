# app/routers/asset_classes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import (
    get_db,
    AssetClass as AssetClassModel,
    Portfolio as PortfolioModel,
    GlobalAssetClass as GlobalAssetClassModel,
    User as UserModel,
)
from app.schemas import AssetClass, AssetClassCreate, AssetClassUpdate, GlobalAssetClass
from app.dependencies import get_current_active_user

router = APIRouter(
    prefix="/asset-classes",
    tags=["Asset Classes"]
)


@router.get("/global-classes", response_model=List[GlobalAssetClass])
def list_global_asset_classes(
    db: Session = Depends(get_db),
    _: UserModel = Depends(get_current_active_user)
):
    """
    Lista classes globais padrão para qualquer usuário autenticado.
    Usado no setup de carteira (passo 2).
    """
    return db.query(GlobalAssetClassModel).order_by(GlobalAssetClassModel.name.asc()).all()

# ==============================================================================
# CREATE - Criar Asset Class
# ==============================================================================

@router.post("/", response_model=AssetClass, status_code=status.HTTP_201_CREATED)
def create_asset_class(
    asset_class: AssetClassCreate,
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova Asset Class (classe de ativos) para um portfolio.

    Args:
        asset_class: Dados da asset class
        portfolio_id: ID do portfolio
        db: Sessão do banco de dados

    Returns:
        Asset class criada

    Raises:
        404: Portfolio não encontrado
        400: Nome duplicado no mesmo portfolio
    """
    # Valida se portfolio existe
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio com ID {portfolio_id} não encontrado"
        )

    # Verifica se já existe asset class com mesmo nome no portfolio
    existing = db.query(AssetClassModel).filter(
        AssetClassModel.portfolio_id == portfolio_id,
        AssetClassModel.name == asset_class.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset class '{asset_class.name}' já existe neste portfolio"
        )

    # Cria asset class
    db_asset_class = AssetClassModel(
        **asset_class.model_dump(),
        portfolio_id=portfolio_id
    )

    db.add(db_asset_class)
    db.commit()
    db.refresh(db_asset_class)

    return db_asset_class

# ==============================================================================
# READ - Listar e Buscar Asset Classes
# ==============================================================================

@router.get("/", response_model=List[AssetClass])
def list_asset_classes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todas as asset classes.

    Args:
        skip: Número de registros para pular
        limit: Número máximo de registros
        db: Sessão do banco de dados

    Returns:
        Lista de asset classes
    """
    asset_classes = db.query(AssetClassModel).offset(skip).limit(limit).all()
    return asset_classes

@router.get("/{asset_class_id}", response_model=AssetClass)
def get_asset_class(
    asset_class_id: int,
    db: Session = Depends(get_db)
):
    """
    Busca uma asset class por ID.

    Args:
        asset_class_id: ID da asset class
        db: Sessão do banco de dados

    Returns:
        Asset class encontrada

    Raises:
        404: Asset class não encontrada
    """
    asset_class = db.query(AssetClassModel).filter(AssetClassModel.id == asset_class_id).first()

    if not asset_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset class com ID {asset_class_id} não encontrada"
        )

    return asset_class

@router.get("/portfolio/{portfolio_id}", response_model=List[AssetClass])
def list_asset_classes_by_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """
    Lista todas as asset classes de um portfolio específico.

    Args:
        portfolio_id: ID do portfolio
        db: Sessão do banco de dados

    Returns:
        Lista de asset classes do portfolio

    Raises:
        404: Portfolio não encontrado
    """
    # Valida se portfolio existe
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio com ID {portfolio_id} não encontrado"
        )

    asset_classes = db.query(AssetClassModel).filter(
        AssetClassModel.portfolio_id == portfolio_id
    ).all()

    return asset_classes

# ==============================================================================
# UPDATE - Atualizar Asset Class
# ==============================================================================

@router.put("/{asset_class_id}", response_model=AssetClass)
def update_asset_class(
    asset_class_id: int,
    asset_class_update: AssetClassUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza uma asset class existente.

    Args:
        asset_class_id: ID da asset class
        asset_class_update: Dados para atualizar
        db: Sessão do banco de dados

    Returns:
        Asset class atualizada

    Raises:
        404: Asset class não encontrada
        400: Nome duplicado no mesmo portfolio
    """
    # Busca asset class
    db_asset_class = db.query(AssetClassModel).filter(AssetClassModel.id == asset_class_id).first()

    if not db_asset_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset class com ID {asset_class_id} não encontrada"
        )

    # Verifica nome duplicado se estiver atualizando nome
    if asset_class_update.name:
        existing = db.query(AssetClassModel).filter(
            AssetClassModel.portfolio_id == db_asset_class.portfolio_id,
            AssetClassModel.name == asset_class_update.name,
            AssetClassModel.id != asset_class_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset class '{asset_class_update.name}' já existe neste portfolio"
            )

    # Atualiza campos
    update_data = asset_class_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_asset_class, field, value)

    db.commit()
    db.refresh(db_asset_class)

    return db_asset_class

# ==============================================================================
# DELETE - Deletar Asset Class
# ==============================================================================

@router.delete("/{asset_class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_class(
    asset_class_id: int,
    db: Session = Depends(get_db)
):
    """
    Deleta uma asset class.

    Args:
        asset_class_id: ID da asset class
        db: Sessão do banco de dados

    Returns:
        None (204 No Content)

    Raises:
        404: Asset class não encontrada
        400: Asset class tem assets associados (não pode deletar)
    """
    # Busca asset class
    db_asset_class = db.query(AssetClassModel).filter(AssetClassModel.id == asset_class_id).first()

    if not db_asset_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset class com ID {asset_class_id} não encontrada"
        )

    # Verifica se tem assets associados
    if db_asset_class.assets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset class '{db_asset_class.name}' tem {len(db_asset_class.assets)} asset(s) associado(s). Delete os assets primeiro."
        )

    # Deleta
    db.delete(db_asset_class)
    db.commit()

    return None
