# app/routers/dashboard.py
"""
Dashboard Router - VERSÃO REFATORADA

NOVA LÓGICA:
- Valor total do portfolio é FIXO (definido pelo usuário)
- Não é calculado pela soma dos ativos
- Classes de ativos têm valor alocado baseado em % meta
- Ativos consomem o "caixa" da classe
- O que não for alocado aparece como CASH

Auto-refresh: Endpoint para atualização de preços a cada 1 minuto
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import asyncio
import math

from app.database import (
    get_db, 
    Portfolio as PortfolioModel, 
    PortfolioAsset as PortfolioAssetModel, 
    Asset as AssetModel, 
    AssetClass as AssetClassModel,
    User as UserModel
)
from app.services.price_service import get_price_service, PriceService
from app.dependencies import get_current_active_user, verify_portfolio_ownership

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# ==============================================================================
# SCHEMAS DE RESPOSTA (inline para evitar dependência circular)
# ==============================================================================

class AssetData:
    """Dados de um ativo para o dashboard."""
    def __init__(self):
        self.id: int = 0
        self.name: str = ""
        self.ticker: str = ""
        self.asset_class_id: int = 0
        self.asset_class_name: str = ""
        self.quantity: float = 0.0
        self.current_price: float = 0.0
        self.current_value: float = 0.0
        self.target_percentage: float = 0.0
        self.current_percentage: float = 0.0  # % no portfolio total
        self.current_percentage_class: float = 0.0  # % na classe
        self.target_percentage_portfolio: float = 0.0  # % meta no portfolio (derivado)
        self.deviation_percentage: float = 0.0  # desvio na classe
        self.deviation_percentage_portfolio: float = 0.0  # desvio no portfolio
        self.rebalance_status: str = ""
        self.rebalance_emoji: str = ""
        self.rebalance_color_class: str = ""
        self.units_to_buy: float = 0.0  # Unidades a comprar para atingir meta
        self.value_to_buy: float = 0.0  # Valor a comprar para atingir meta
        self.price_source: str = ""
        self.price_error: str = ""


class AssetClassData:
    """Dados de uma classe de ativos para o dashboard."""
    def __init__(self):
        self.id: int = 0
        self.name: str = ""
        self.target_percentage: float = 0.0
        self.target_value: float = 0.0  # Valor que deveria ter (% do total)
        self.allocated_value: float = 0.0  # Valor já alocado em ativos
        self.cash_value: float = 0.0  # Valor em CASH (não alocado)
        self.current_percentage: float = 0.0  # % real atual
        self.deviation_percentage: float = 0.0
        self.deviation_status: str = ""  # OK, SUB-ALOCADO, SOBRE-ALOCADO
        self.deviation_icon: str = ""
        self.assets: List[AssetData] = []


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def calculate_rebalance_status(deviation_abs: float, threshold: float) -> tuple:
    """
    Calcula status de rebalanceamento baseado no desvio.
    Retorna: (status, emoji, css_class)
    """
    threshold_orange = threshold
    threshold_red = threshold * 1.20
    threshold_purple = threshold_red * 1.20
    
    if math.isclose(deviation_abs, 0.0, abs_tol=0.001) or deviation_abs < threshold_orange:
        return "OK", "✅", "text-green-600"
    elif deviation_abs < threshold_red:
        return "Alerta", "⚠️", "text-orange-500"
    elif deviation_abs < threshold_purple:
        return "Crítico", "🚨", "text-red-600"
    else:
        return "Extremamente Crítico", "💥", "text-purple-700"


def calculate_class_deviation_status(target_pct: float, current_pct: float) -> tuple:
    """
    Calcula status de desvio da classe de ativos.
    - SUB-ALOCADO: Real < 90% da Meta
    - SOBRE-ALOCADO: Real > 110% da Meta
    - OK: Entre 90% e 110%
    
    Retorna: (status, icon)
    """
    if target_pct == 0:
        return "OK", "🟢", "text-blue-700"
    
    ratio = current_pct / target_pct if target_pct > 0 else 0
    
    if ratio < 0.90:
        return "SUB-ALOCADO", "⚠️", "text-red-700"  # Vermelho escuro
    elif ratio > 1.10:
        return "SOBRE-ALOCADO", "🔶", "text-green-700"  # Verde escuro
    else:
        return "OK", "🟢", "text-blue-700"


# ==============================================================================
# ENDPOINT: ATUALIZAR PREÇOS
# ==============================================================================

@router.post("/update-prices/{portfolio_id}")
async def update_prices(portfolio_id: int, db: Session = Depends(get_db)):
    """
    Atualiza os preços de todos os ativos do portfolio.
    Chamado pelo frontend a cada 1 minuto (auto-refresh).
    """
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")
    
    # Busca todos os ativos do portfolio
    portfolio_assets = db.query(PortfolioAssetModel).options(
        joinedload(PortfolioAssetModel.asset)
    ).filter(PortfolioAssetModel.portfolio_id == portfolio_id).all()
    
    if not portfolio_assets:
        return {
            "success": True,
            "message": "Nenhum ativo para atualizar",
            "updated_at": datetime.now().isoformat(),
            "updated_count": 0,
            "error_count": 0,
            "errors": []
        }
    
    # Coleta tickers únicos
    tickers = list(set(pa.asset.ticker for pa in portfolio_assets if pa.asset))
    
    # Busca preços em paralelo
    price_service = get_price_service()
    prices = await price_service.get_prices_batch(tickers)
    
    # Atualiza assets no banco
    updated_count = 0
    error_count = 0
    errors = []
    
    for pa in portfolio_assets:
        if not pa.asset:
            continue
        
        ticker = pa.asset.ticker
        if ticker in prices:
            price, source, error = prices[ticker]
            
            if price > 0:
                pa.asset.last_price = price
                pa.asset.last_price_updated = datetime.now()
                pa.asset.price_source = source
                updated_count += 1
            else:
                error_count += 1
                if error:
                    errors.append(f"{ticker}: {error}")
    
    # Atualiza timestamp do portfolio
    portfolio.last_prices_updated = datetime.now()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Atualizados {updated_count} de {len(tickers)} ativos",
        "updated_at": portfolio.last_prices_updated.isoformat(),
        "updated_count": updated_count,
        "error_count": error_count,
        "errors": errors[:5]  # Limita a 5 erros para não poluir
    }


# ==============================================================================
# ENDPOINT: DADOS DO DASHBOARD (API JSON)
# ==============================================================================

@router.get("/api/{portfolio_id}")
def get_dashboard_data(portfolio_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna dados estruturados do dashboard.
    
    NOVA LÓGICA:
    - total_portfolio_value = valor FIXO definido pelo usuário
    - Cada classe tem valor_alvo = total * %_meta_classe
    - Ativos consomem o valor da classe
    - CASH = valor_alvo - valor_alocado
    """
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")
    
    # Valor total FIXO (definido pelo usuário)
    total_value = portfolio.total_value or 0.0
    
    # Busca classes de ativos do portfolio
    asset_classes = db.query(AssetClassModel).filter(
        AssetClassModel.portfolio_id == portfolio_id
    ).all()
    
    # Busca portfolio_assets com joins
    portfolio_assets = db.query(PortfolioAssetModel).options(
        joinedload(PortfolioAssetModel.asset).joinedload(AssetModel.asset_class)
    ).filter(PortfolioAssetModel.portfolio_id == portfolio_id).all()
    
    # Agrupa ativos por classe
    assets_by_class: Dict[int, List[PortfolioAssetModel]] = {}
    for pa in portfolio_assets:
        if pa.asset and pa.asset.asset_class_id:
            class_id = pa.asset.asset_class_id
            if class_id not in assets_by_class:
                assets_by_class[class_id] = []
            assets_by_class[class_id].append(pa)
    
    # Calcula valor total REAL (soma dos ativos com preços)
    total_real_value = 0.0
    for pa in portfolio_assets:
        if pa.asset:
            price = pa.asset.last_price or 0.0
            total_real_value += pa.quantity * price
    
    # Monta dados das classes
    classes_data: List[Dict] = []
    alerts: List[str] = []
    all_assets_data: List[Dict] = []
    
    for ac in asset_classes:
        class_data = AssetClassData()
        class_data.id = ac.id
        class_data.name = ac.name
        class_data.target_percentage = ac.target_percentage
        class_data.target_value = (ac.target_percentage / 100) * total_value if total_value > 0 else 0
        
        # Calcula valor alocado nos ativos desta classe
        class_assets = assets_by_class.get(ac.id, [])
        allocated = 0.0
        
        for pa in class_assets:
            asset = pa.asset
            if not asset:
                continue
            
            current_price = asset.last_price or 0.0
            current_value = pa.quantity * current_price
            allocated += current_value
            
            # Monta dados do ativo
            asset_data = {
                "id": pa.id,
                "name": asset.name,
                "ticker": asset.ticker,
                "asset_class_id": ac.id,
                "asset_class_name": ac.name,
                "quantity": pa.quantity,
                "current_price": current_price,
                "current_value": current_value,
                "target_percentage": pa.target_percentage,  # % meta dentro da classe
                "target_percentage_portfolio": 0.0,  # % meta no portfolio (derivado)
                "current_percentage": 0.0,  # % atual no portfolio
                "current_percentage_class": 0.0,  # % atual na classe
                "deviation_percentage": 0.0,  # desvio na classe
                "deviation_percentage_portfolio": 0.0,  # desvio no portfolio
                "rebalance_status": "OK",
                "rebalance_emoji": "✅",
                "rebalance_color_class": "text-green-600",
                "units_to_buy": 0.0,
                "value_to_buy": 0.0,
                "price_source": asset.price_source or "",
                "price_error": "" if current_price > 0 else "Preço não disponível"
            }
            
            # Calcula % atual e desvio
            # % atual no portfolio
            if total_value > 0:
                asset_data["current_percentage"] = (current_value / total_value) * 100

            # % meta no portfolio (derivado da classe)
            if class_data.target_percentage > 0:
                asset_data["target_percentage_portfolio"] = (
                    class_data.target_percentage * (pa.target_percentage / 100)
                )
                asset_data["deviation_percentage_portfolio"] = (
                    asset_data["current_percentage"] - asset_data["target_percentage_portfolio"]
                )

            # % atual e desvio na classe
            if class_data.target_value > 0:
                asset_data["current_percentage_class"] = (current_value / class_data.target_value) * 100
                asset_data["deviation_percentage"] = asset_data["current_percentage_class"] - pa.target_percentage

                # Status de rebalanceamento (baseado na classe)
                deviation_abs = abs(asset_data["deviation_percentage"])
                status, emoji, css = calculate_rebalance_status(deviation_abs, pa.rebalance_threshold_percentage)
                asset_data["rebalance_status"] = status
                asset_data["rebalance_emoji"] = emoji
                asset_data["rebalance_color_class"] = css

                # Calcula unidades a comprar/vender (meta na classe)
                if current_price > 0:
                    target_value = (pa.target_percentage / 100) * class_data.target_value
                    value_diff = target_value - current_value
                    asset_data["value_to_buy"] = value_diff
                    asset_data["units_to_buy"] = value_diff / current_price
            
            class_data.assets.append(asset_data)
            all_assets_data.append(asset_data)
            
            # Alerta se preço não disponível
            if current_price == 0:
                alerts.append(f"Preço não disponível para {asset.ticker}")
        
        class_data.allocated_value = allocated
        class_data.cash_value = max(0, class_data.target_value - allocated)
        
        # Calcula % real da classe
        if total_value > 0:
            class_data.current_percentage = (allocated / total_value) * 100
        
        class_data.deviation_percentage = class_data.current_percentage - class_data.target_percentage
        
        # Status de desvio da classe
        status, icon, color = calculate_class_deviation_status(
            class_data.target_percentage, 
            class_data.current_percentage
        )
        class_data.deviation_status = status
        class_data.deviation_icon = icon
        class_data.deviation_color_class = color
        
        classes_data.append({
            "id": class_data.id,
            "name": class_data.name,
            "target_percentage": class_data.target_percentage,
            "target_value": class_data.target_value,
            "allocated_value": class_data.allocated_value,
            "cash_value": class_data.cash_value,
            "current_percentage": class_data.current_percentage,
            "deviation_percentage": class_data.deviation_percentage,
            "deviation_status": class_data.deviation_status,
            "deviation_icon": class_data.deviation_icon,
            "deviation_color_class": class_data.deviation_color_class,
            "assets": [a for a in all_assets_data if a["asset_class_id"] == ac.id]
        })
    
    # Calcula CASH geral (valor não alocado em nenhuma classe)
    total_class_target = sum(ac.target_percentage for ac in asset_classes)
    unallocated_percentage = max(0, 100 - total_class_target)
    unallocated_value = (unallocated_percentage / 100) * total_value if total_value > 0 else 0
    
    return {
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "total_portfolio_value": total_value,  # Valor FIXO
        "total_real_value": total_real_value,  # Valor calculado (soma dos ativos)
        "currency": portfolio.currency or "USD",
        "last_prices_updated": portfolio.last_prices_updated.isoformat() if portfolio.last_prices_updated else None,
        "dashboard_template": getattr(portfolio, "dashboard_template", "v1") or "v1",
        "asset_classes": classes_data,
        "assets_data": all_assets_data,
        "alerts": alerts,
        "unallocated_percentage": unallocated_percentage,
        "unallocated_value": unallocated_value,
        "summary": {
            "total_classes": len(asset_classes),
            "total_assets": len(all_assets_data),
            "total_allocated": total_real_value,
            "total_cash": total_value - total_real_value if total_value > total_real_value else 0
        }
    }


# ==============================================================================
# ENDPOINT: DASHBOARD HTML
# ==============================================================================

class DashboardTemplateUpdate(BaseModel):
    template: str


@router.post("/template/{portfolio_id}")
def update_dashboard_template(
    portfolio_id: int,
    payload: DashboardTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza o template preferido do dashboard para o portfólio."""
    template = (payload.template or "v1").lower()
    if template not in {"v1", "v2", "v3"}:
        raise HTTPException(status_code=400, detail="Template inválido")
    portfolio = db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")
    portfolio.dashboard_template = template
    db.commit()
    return {"success": True, "template": template}

@router.get("/", response_class=HTMLResponse)
async def dashboard_html(
    request: Request,
    portfolio_id: int,
    template: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Renderiza a página do dashboard."""
    try:
        verify_portfolio_ownership(portfolio_id, current_user, db)
        data = get_dashboard_data(portfolio_id, db)
        
        context = {
            "request": request,
            "title": f"Dashboard - {data['portfolio_name']}",
            **data,
            "current_user": current_user
        }
        if template in {"v1", "v2", "v3"}:
            data["dashboard_template"] = template
        template = data.get("dashboard_template") or "v1"
        if template == "v2":
            return templates.TemplateResponse("dashboard_v2.html", context)
        if template == "v3":
            return templates.TemplateResponse("dashboard_v3.html", context)
        return templates.TemplateResponse("dashboard.html", context)
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro", "message": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro Inesperado", "message": str(e)},
            status_code=500
        )


@router.get("/preview", response_class=HTMLResponse)
async def dashboard_preview(
    request: Request,
    portfolio_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Renderiza a versão de preview do dashboard (layout novo)."""
    try:
        verify_portfolio_ownership(portfolio_id, current_user, db)
        data = get_dashboard_data(portfolio_id, db)
        context = {
            "request": request,
            "title": f"Dashboard (Preview) - {data['portfolio_name']}",
            **data,
            "current_user": current_user
        }
        return templates.TemplateResponse("dashboard_v2.html", context)
    except HTTPException as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro", "message": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro Inesperado", "message": str(e)},
            status_code=500
        )


@router.get("/preview-v3", response_class=HTMLResponse)
async def dashboard_preview_v3(
    request: Request,
    portfolio_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Renderiza a versão v3 do dashboard (layout discreto)."""
    try:
        verify_portfolio_ownership(portfolio_id, current_user, db)
        data = get_dashboard_data(portfolio_id, db)
        context = {
            "request": request,
            "title": f"Dashboard V3 - {data['portfolio_name']}",
            **data,
            "current_user": current_user
        }
        return templates.TemplateResponse("dashboard_v3.html", context)
    except HTTPException as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro", "message": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Erro Inesperado", "message": str(e)},
            status_code=500
        )


# ==============================================================================
# ENDPOINT: DADOS PARA GRÁFICOS
# ==============================================================================

@router.get("/charts/{portfolio_id}")
def get_charts_data(portfolio_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna dados formatados para os gráficos:
    - Pizza 3D (classes de ativos)
    - Barras (Meta vs Real)
    """
    data = get_dashboard_data(portfolio_id, db)
    
    # Dados para gráfico de pizza
    pie_data = []
    for ac in data["asset_classes"]:
        pie_data.append({
            "name": ac["name"],
            "target_percentage": ac["target_percentage"],
            "target_value": ac["target_value"],
            "allocated_value": ac["allocated_value"],
            "cash_value": ac["cash_value"],
            "assets": ac["assets"]
        })
    
    # Adiciona CASH geral se houver
    if data["unallocated_value"] > 0:
        pie_data.append({
            "name": "CASH (Não Alocado)",
            "target_percentage": data["unallocated_percentage"],
            "target_value": data["unallocated_value"],
            "allocated_value": 0,
            "cash_value": data["unallocated_value"],
            "assets": []
        })
    
    # Dados para gráfico de barras (Meta vs Real)
    bar_data = []
    for ac in data["asset_classes"]:
        bar_data.append({
            "name": ac["name"],
            "target": ac["target_percentage"],
            "real": ac["current_percentage"],
            "status": ac["deviation_status"],
            "icon": ac["deviation_icon"]
        })
    
    return {
        "pie_chart": pie_data,
        "bar_chart": bar_data,
        "total_value": data["total_portfolio_value"],
        "currency": data["currency"]
    }
