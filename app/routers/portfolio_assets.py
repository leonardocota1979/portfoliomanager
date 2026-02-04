# app/routers/portfolio_assets.py
"""
Router de Portfolio Assets - VERSÃO CORRIGIDA

Correções:
- asset_id vem do BODY (PortfolioAssetCreate), não como query param
- portfolio_id vem como query parameter
- Não duplica parâmetros
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from ..database import (
    get_db, 
    PortfolioAsset as PortfolioAssetModel, 
    Portfolio as PortfolioModel,
    Asset as AssetModel
)
from .. import schemas

router = APIRouter(
    prefix="/portfolio-assets",
    tags=["Portfolio Assets"]
)


# ==============================================================================
# CREATE - Adicionar ativo ao portfolio
# ==============================================================================

@router.post("/", response_model=schemas.PortfolioAsset)
def create_portfolio_asset(
    portfolio_asset: schemas.PortfolioAssetCreate,
    portfolio_id: int = Query(..., description="ID do portfolio"),
    db: Session = Depends(get_db)
):
    """
    Adiciona um ativo a um portfolio.
    
    - portfolio_id: vem como QUERY PARAMETER
    - asset_id: vem no BODY (PortfolioAssetCreate)
    - quantity, target_percentage: vem no BODY
    """
    # Verifica se portfolio existe
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio com ID {portfolio_id} não encontrado"
        )
    
    # Verifica se asset existe
    asset = db.query(AssetModel).filter(AssetModel.id == portfolio_asset.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ID {portfolio_asset.asset_id} não encontrado"
        )
    
    # Verifica se já existe no portfolio
    existing = db.query(PortfolioAssetModel).filter(
        PortfolioAssetModel.portfolio_id == portfolio_id,
        PortfolioAssetModel.asset_id == portfolio_asset.asset_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {asset.ticker} já existe neste portfolio"
        )
    
    # Cria o portfolio_asset
    db_portfolio_asset = PortfolioAssetModel(
        portfolio_id=portfolio_id,
        asset_id=portfolio_asset.asset_id,
        quantity=portfolio_asset.quantity,
        target_percentage=portfolio_asset.target_percentage,
        rebalance_threshold_percentage=portfolio_asset.rebalance_threshold_percentage
    )
    
    db.add(db_portfolio_asset)
    db.commit()
    db.refresh(db_portfolio_asset)
    
    return db_portfolio_asset


# ==============================================================================
# READ - Listar e Buscar
# ==============================================================================

@router.get("/", response_model=List[schemas.PortfolioAsset])
def list_portfolio_assets(
    portfolio_id: int = Query(None, description="Filtrar por portfolio"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista portfolio assets, opcionalmente filtrados por portfolio."""
    query = db.query(PortfolioAssetModel)
    
    if portfolio_id:
        query = query.filter(PortfolioAssetModel.portfolio_id == portfolio_id)
    
    return query.offset(skip).limit(limit).all()


@router.get("/{portfolio_asset_id}", response_model=schemas.PortfolioAsset)
def get_portfolio_asset(
    portfolio_asset_id: int,
    db: Session = Depends(get_db)
):
    """Busca um portfolio asset por ID."""
    pa = db.query(PortfolioAssetModel).filter(
        PortfolioAssetModel.id == portfolio_asset_id
    ).first()
    
    if not pa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PortfolioAsset com ID {portfolio_asset_id} não encontrado"
        )
    
    return pa


@router.get("/portfolio/{portfolio_id}/details")
def get_portfolio_assets_details(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna detalhes completos dos ativos de um portfolio.
    Inclui dados do Asset relacionado.
    """
    portfolio_assets = db.query(PortfolioAssetModel).options(
        joinedload(PortfolioAssetModel.asset)
    ).filter(
        PortfolioAssetModel.portfolio_id == portfolio_id
    ).all()
    
    result = []
    for pa in portfolio_assets:
        asset = pa.asset
        result.append({
            "id": pa.id,
            "portfolio_id": pa.portfolio_id,
            "asset_id": pa.asset_id,
            "quantity": pa.quantity,
            "target_percentage": pa.target_percentage,
            "rebalance_threshold_percentage": pa.rebalance_threshold_percentage,
            "asset": {
                "id": asset.id if asset else None,
                "name": asset.name if asset else "N/A",
                "ticker": asset.ticker if asset else "N/A",
                "last_price": asset.last_price if asset else 0,
                "price_source": asset.price_source if asset else None
            } if asset else None
        })
    
    return result


# ==============================================================================
# UPDATE - Atualizar
# ==============================================================================

@router.put("/{portfolio_asset_id}", response_model=schemas.PortfolioAsset)
def update_portfolio_asset(
    portfolio_asset_id: int,
    portfolio_asset: schemas.PortfolioAssetUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza um portfolio asset (quantidade, % meta, threshold)."""
    db_pa = db.query(PortfolioAssetModel).filter(
        PortfolioAssetModel.id == portfolio_asset_id
    ).first()
    
    if not db_pa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PortfolioAsset com ID {portfolio_asset_id} não encontrado"
        )
    
    update_data = portfolio_asset.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_pa, key, value)
    
    db.commit()
    db.refresh(db_pa)
    
    return db_pa


# ==============================================================================
# DELETE - Remover
# ==============================================================================

@router.delete("/{portfolio_asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_asset(
    portfolio_asset_id: int,
    db: Session = Depends(get_db)
):
    """Remove um ativo do portfolio."""
    db_pa = db.query(PortfolioAssetModel).filter(
        PortfolioAssetModel.id == portfolio_asset_id
    ).first()
    
    if not db_pa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PortfolioAsset com ID {portfolio_asset_id} não encontrado"
        )
    
    db.delete(db_pa)
    db.commit()
    
    return None
