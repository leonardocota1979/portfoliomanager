# app/routers/assets.py
"""
Router de Assets - VERSÃO CORRIGIDA

Correções:
- Não duplica asset_class_id (usa apenas o do body)
- Normaliza ticker para uppercase
- Endpoint para atualizar preço manualmente
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from ..database import get_db, Asset as AssetModel, AssetClass as AssetClassModel, Portfolio as PortfolioModel
from .. import crud
from .. import schemas
from ..services.price_service import get_price_service

router = APIRouter(
    prefix="/assets",
    tags=["Assets"]
)


# ==============================================================================
# CREATE - Criar Asset
# ==============================================================================

@router.post("/", response_model=schemas.Asset)
def create_asset(
    asset: schemas.AssetCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo asset.
    
    O asset_class_id vem NO BODY (AssetCreate), não como query parameter.
    """
    # Normaliza ticker
    ticker = asset.ticker.upper().strip()
    
    # Verifica se ticker já existe na mesma classe
    existing = db.query(AssetModel).filter(
        AssetModel.ticker == ticker,
        AssetModel.asset_class_id == asset.asset_class_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset com ticker '{ticker}' já existe nesta classe (ID: {existing.id})"
        )
    
    # Verifica se asset_class existe
    asset_class = db.query(AssetClassModel).filter(
        AssetClassModel.id == asset.asset_class_id
    ).first()
    
    if not asset_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AssetClass com ID {asset.asset_class_id} não encontrada"
        )
    
    # Cria o asset usando model_dump() que já inclui asset_class_id
    asset_data = asset.model_dump()
    asset_data['ticker'] = ticker  # Garante uppercase
    
    db_asset = AssetModel(**asset_data)
    
    db.add(db_asset)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um asset com este ticker. Execute a migração de unicidade por classe."
        )
    db.refresh(db_asset)
    
    return db_asset


# ==============================================================================
# READ - Listar e Buscar Assets
# ==============================================================================

@router.get("/", response_model=List[schemas.Asset])
def list_assets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista todos os assets."""
    assets = db.query(AssetModel).offset(skip).limit(limit).all()
    return assets


@router.get("/{asset_id}", response_model=schemas.Asset)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """Busca um asset por ID."""
    asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ID {asset_id} não encontrado"
        )
    return asset


@router.get("/ticker/{ticker}")
def get_asset_by_ticker(
    ticker: str,
    asset_class_id: int | None = None,
    db: Session = Depends(get_db)
):
    """Busca um asset por ticker (opcionalmente por classe)."""
    ticker = ticker.upper().strip()
    if asset_class_id:
        asset = crud.get_asset_by_ticker_and_class(db, ticker, asset_class_id)
    else:
        asset = db.query(AssetModel).filter(AssetModel.ticker == ticker).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ticker '{ticker}' não encontrado"
        )
    
    return {
        "id": asset.id,
        "name": asset.name,
        "ticker": asset.ticker,
        "asset_class_id": asset.asset_class_id,
        "source": asset.source,
        "last_price": asset.last_price,
        "last_price_updated": asset.last_price_updated.isoformat() if asset.last_price_updated else None,
        "price_source": asset.price_source
    }


@router.get("/class/{asset_class_id}", response_model=List[schemas.Asset])
def list_assets_by_class(
    asset_class_id: int,
    db: Session = Depends(get_db)
):
    """Lista assets de uma classe específica."""
    assets = db.query(AssetModel).filter(
        AssetModel.asset_class_id == asset_class_id
    ).all()
    return assets


# ==============================================================================
# UPDATE - Atualizar Asset
# ==============================================================================

@router.put("/{asset_id}", response_model=schemas.Asset)
def update_asset(
    asset_id: int,
    asset: schemas.AssetUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza um asset."""
    db_asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    
    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ID {asset_id} não encontrado"
        )
    
    update_data = asset.model_dump(exclude_unset=True)
    
    # Se atualizou ticker, normaliza e verifica duplicidade
    if 'ticker' in update_data:
        new_ticker = update_data['ticker'].upper().strip()
        existing = db.query(AssetModel).filter(
            AssetModel.ticker == new_ticker,
            AssetModel.id != asset_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticker '{new_ticker}' já existe em outro asset"
            )
        
        update_data['ticker'] = new_ticker
    
    for key, value in update_data.items():
        setattr(db_asset, key, value)
    
    db.commit()
    db.refresh(db_asset)
    
    return db_asset


# ==============================================================================
# UPDATE PRICE - Atualizar preço manualmente
# ==============================================================================

@router.put("/update-price/{ticker}")
def update_asset_price(
    ticker: str,
    price_data: dict,
    db: Session = Depends(get_db)
):
    """
    Atualiza o preço de um asset manualmente.
    
    Útil quando a busca automática não funciona.
    
    Body: {"price": 123.45}
    """
    ticker = ticker.upper().strip()
    
    asset = db.query(AssetModel).filter(AssetModel.ticker == ticker).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ticker '{ticker}' não encontrado"
        )
    
    price = price_data.get('price', 0)
    
    if price and float(price) > 0:
        asset.last_price = float(price)
        asset.last_price_updated = datetime.now()
        asset.price_source = 'manual'
        
        db.commit()
        db.refresh(asset)
    
    return {
        "ticker": asset.ticker,
        "price": asset.last_price,
        "source": asset.price_source,
        "updated_at": asset.last_price_updated.isoformat() if asset.last_price_updated else None
    }


# ==============================================================================
# SUGGEST QUANTITY - Sugere quantidade para atingir % da classe
# ==============================================================================

@router.post("/suggest-quantity")
async def suggest_quantity(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Sugere quantidade com base no % meta dentro da classe.
    Body:
      {
        "portfolio_id": 1,
        "asset_class_id": 2,
        "ticker": "AAPL",
        "target_pct_class": 50.0
      }
    """
    portfolio_id = payload.get("portfolio_id")
    asset_class_id = payload.get("asset_class_id")
    ticker = str(payload.get("ticker", "")).upper().strip()
    target_pct_class = float(payload.get("target_pct_class") or 0)

    if not portfolio_id or not asset_class_id or not ticker or target_pct_class <= 0:
        raise HTTPException(status_code=400, detail="Dados inválidos")

    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")

    asset_class = db.query(AssetClassModel).filter(AssetClassModel.id == asset_class_id).first()
    if not asset_class:
        raise HTTPException(status_code=404, detail="Classe não encontrada")

    portfolio_total = portfolio.total_value or 0.0
    class_target_pct = asset_class.target_percentage or 0.0
    class_target_value = (class_target_pct / 100.0) * portfolio_total

    used_fallback = False
    if class_target_value <= 0 and portfolio_total > 0:
        # Fallback: se a classe não tem meta definida, usa o total do portfólio
        class_target_value = portfolio_total
        used_fallback = True

    target_value = (target_pct_class / 100.0) * class_target_value

    if target_value <= 0:
        return {
            "quantity": 0,
            "price": 0,
            "source": "",
            "target_value": 0,
            "reason": "target_value_zero",
            "portfolio_total_value": portfolio_total,
            "class_target_percentage": class_target_pct,
            "class_target_value": class_target_value,
            "used_fallback": used_fallback
        }

    price_service = get_price_service()
    price, sources, _ = await price_service.get_price_consensus(ticker)

    if not price or price <= 0:
        return {
            "quantity": 0,
            "price": 0,
            "source": "",
            "target_value": target_value,
            "reason": "price_not_found",
            "portfolio_total_value": portfolio_total,
            "class_target_percentage": class_target_pct,
            "class_target_value": class_target_value,
            "used_fallback": used_fallback
        }

    quantity = target_value / price
    return {
        "quantity": quantity,
        "price": price,
        "source": sources,
        "target_value": target_value,
        "reason": "fallback_portfolio" if used_fallback else "",
        "portfolio_total_value": portfolio_total,
        "class_target_percentage": class_target_pct,
        "class_target_value": class_target_value,
        "used_fallback": used_fallback
    }


# ==============================================================================
# DELETE - Deletar Asset
# ==============================================================================

@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """Deleta um asset."""
    db_asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    
    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset com ID {asset_id} não encontrado"
        )
    
    db.delete(db_asset)
    db.commit()
    
    return None
