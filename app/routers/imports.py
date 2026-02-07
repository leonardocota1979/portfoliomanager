"""
Router de importação via OCR (prints) com preview e confirmação.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import (
    get_db,
    Portfolio as PortfolioModel,
    AssetClass as AssetClassModel,
    Asset as AssetModel,
    PortfolioAsset as PortfolioAssetModel,
    AssetClassMapping as AssetClassMappingModel,
    GlobalAssetClass as GlobalAssetClassModel,
    User as UserModel,
)
from app.dependencies import get_current_active_user
from app.services.import_service import run_tesseract, parse_positions, detect_currency, TOP_CURRENCIES, imp_logger
from app.services.price_service import get_price_service
from app.core.settings import get_settings
import difflib

router = APIRouter(prefix="/imports", tags=["Imports"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
SETTINGS = get_settings()


def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{upload.filename}"
    path = dest_dir / filename
    with path.open("wb") as f:
        f.write(upload.file.read())
    return path


def _get_portfolio_classes(db: Session, portfolio_id: int) -> List[str]:
    classes = db.query(AssetClassModel).filter(AssetClassModel.portfolio_id == portfolio_id).all()
    return [c.name for c in classes]


def _get_mapping_classes(db: Session, ticker: str) -> List[str]:
    rows = db.query(AssetClassMappingModel).filter(AssetClassMappingModel.ticker == ticker).all()
    return sorted({r.class_name for r in rows})


def _get_similar_tickers(db: Session, ticker: str) -> List[str]:
    ticker = ticker.upper().strip()
    popular = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","SPY","QQQ","VOO","VTI","BTC-USD","ETH-USD"]
    assets = [r[0] for r in db.query(AssetModel.ticker).distinct().all()]
    mappings = [r[0] for r in db.query(AssetClassMappingModel.ticker).distinct().all()]
    candidates = list(set(popular + assets + mappings))
    return difflib.get_close_matches(ticker, candidates, n=5, cutoff=0.6)


@router.get("/", response_class=HTMLResponse)
def import_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    portfolios = db.query(PortfolioModel).filter(PortfolioModel.owner_id == current_user.id).all()
    return templates.TemplateResponse(
        "portfolio_import.html",
        {"request": request, "title": "Importar Portfólio", "portfolios": portfolios, "current_user": current_user}
    )


@router.get("/portfolio-summary/{portfolio_id}")
def portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.owner_id == current_user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")

    items = (
        db.query(PortfolioAssetModel, AssetModel, AssetClassModel)
        .join(AssetModel, PortfolioAssetModel.asset_id == AssetModel.id)
        .join(AssetClassModel, AssetModel.asset_class_id == AssetClassModel.id)
        .filter(PortfolioAssetModel.portfolio_id == portfolio_id)
        .all()
    )

    assets = []
    for pa, asset, cls in items:
        assets.append({
            "ticker": asset.ticker,
            "name": asset.name,
            "quantity": pa.quantity,
            "class_name": cls.name
        })

    return {
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "currency": portfolio.currency or "USD",
        "assets": assets,
        "classes": _get_portfolio_classes(db, portfolio.id)
    }


@router.post("/preview")
async def import_preview(
    source: str = Form(...),
    portfolio_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    upload_dir = SETTINGS.upload_dir
    path = _save_upload(file, upload_dir)
    imp_logger.info("preview upload=%s source=%s portfolio_id=%s", path, source, portfolio_id)

    text = run_tesseract(path)
    positions = parse_positions(text, source)
    currency = detect_currency(text)

    # consolida por ticker para evitar duplicatas
    consolidated: Dict[str, Dict[str, Any]] = {}
    for p in positions:
        key = p.ticker.upper().strip()
        if key.endswith("USD") and "-" not in key and len(key) > 3:
            key = f"{key[:-3]}-USD"
        entry = consolidated.get(key, {"ticker": key, "name": p.name, "quantity": 0.0})
        entry["quantity"] += float(p.quantity or 0)
        consolidated[key] = entry

    tickers = [v["ticker"] for v in consolidated.values()]
    price_service = get_price_service()
    price_tasks = [price_service.get_price_consensus(t) for t in tickers]
    prices = await asyncio.gather(*price_tasks, return_exceptions=True)

    items = []
    available_classes = []
    if portfolio_id:
        portfolio = db.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id,
            PortfolioModel.owner_id == current_user.id
        ).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio não encontrado")
        available_classes = _get_portfolio_classes(db, portfolio_id)
    else:
        global_classes = db.query(GlobalAssetClassModel).all()
        available_classes = [c.name for c in global_classes]
    for pos, price_res in zip(consolidated.values(), prices):
        price, sources, diverged = (0.0, "", True)
        if not isinstance(price_res, Exception):
            price, sources, diverged = price_res
        suggested_classes = _get_mapping_classes(db, pos["ticker"])
        suggestions = _get_similar_tickers(db, pos["ticker"]) if price == 0 else []
        items.append({
            "ticker": pos["ticker"],
            "name": pos["name"],
            "quantity": pos["quantity"],
            "price": price,
            "price_sources": sources,
            "price_diverged": diverged,
            "suggested_classes": suggested_classes,
            "ticker_suggestions": suggestions
        })

    return {
        "detected_currency": currency,
        "top_currencies": TOP_CURRENCIES,
        "items": items,
        "available_classes": available_classes
    }


@router.post("/confirm")
def import_confirm(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    portfolio_id = payload.get("portfolio_id")
    new_portfolio_name = payload.get("new_portfolio_name")
    currency = payload.get("currency") or "USD"
    total_value = payload.get("total_value")
    items = payload.get("items", [])

    if not items:
        raise HTTPException(status_code=400, detail="Nenhum item para importar")

    if portfolio_id:
        portfolio = db.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id,
            PortfolioModel.owner_id == current_user.id
        ).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio não encontrado")
    else:
        if not new_portfolio_name:
            raise HTTPException(status_code=400, detail="Nome do portfólio é obrigatório")
        portfolio = PortfolioModel(
            name=new_portfolio_name,
            description="Importado via OCR",
            total_value=total_value or 0.0,
            currency=currency,
            owner_id=current_user.id
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    for item in items:
        ticker = str(item.get("ticker", "")).upper().strip()
        name = str(item.get("name", ticker)).strip() or ticker
        quantity = float(item.get("quantity") or 0)
        class_name = str(item.get("class_name", "")).strip()
        possible_classes = item.get("possible_classes") or []
        price = float(item.get("price") or 0)
        price_sources = item.get("price_sources") or ""

        if not ticker or quantity <= 0 or not class_name:
            continue

        # cria classe se não existir no portfolio
        asset_class = (
            db.query(AssetClassModel)
            .filter(AssetClassModel.portfolio_id == portfolio.id, AssetClassModel.name == class_name)
            .first()
        )
        if not asset_class:
            asset_class = AssetClassModel(
                name=class_name,
                target_percentage=0.0,
                portfolio_id=portfolio.id,
                is_custom=True,
            )
            db.add(asset_class)
            db.commit()
            db.refresh(asset_class)

        # registra mapeamentos possíveis
        for cls_name in set([class_name] + [str(c).strip() for c in possible_classes if str(c).strip()]):
            mapping = (
                db.query(AssetClassMappingModel)
                .filter(AssetClassMappingModel.ticker == ticker, AssetClassMappingModel.class_name == cls_name)
                .first()
            )
            if not mapping:
                db.add(AssetClassMappingModel(ticker=ticker, class_name=cls_name))
                db.commit()

        # cria/usa asset por classe
        asset = (
            db.query(AssetModel)
            .filter(AssetModel.ticker == ticker, AssetModel.asset_class_id == asset_class.id)
            .first()
        )
        if not asset:
            asset = AssetModel(
                name=name,
                ticker=ticker,
                asset_class_id=asset_class.id,
                source="import"
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

        if price > 0:
            asset.last_price = price
            asset.last_price_updated = datetime.now()
            asset.price_source = price_sources
            db.commit()

        # adiciona/concatena portfolio_asset
        pa = (
            db.query(PortfolioAssetModel)
            .filter(PortfolioAssetModel.portfolio_id == portfolio.id, PortfolioAssetModel.asset_id == asset.id)
            .first()
        )
        if pa:
            pa.quantity = (pa.quantity or 0) + quantity
            db.commit()
        else:
            pa = PortfolioAssetModel(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                quantity=quantity,
                target_percentage=0.0,
                rebalance_threshold_percentage=5.0
            )
            db.add(pa)
            db.commit()

    imp_logger.info("import confirm portfolio_id=%s items=%d", portfolio.id, len(items))

    return {"success": True, "portfolio_id": portfolio.id}
