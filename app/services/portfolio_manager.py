# app/services/portfolio_manager.py
# Lógica de gerenciamento de portfolios e cálculos

from sqlalchemy.orm import Session
from typing import Dict, List, Any
from .. import crud, database as models
from .financial_data import get_current_price
import asyncio

async def calculate_portfolio_value(db: Session, portfolio_id: int) -> Dict[str, Any]:
    """
    Calcula o valor total de um portfolio e suas métricas.

    Args:
        db: Sessão do banco de dados
        portfolio_id: ID do portfolio

    Returns:
        dict: Métricas do portfolio (valor total, alocações, alertas)
    """
    # Busca todos os ativos do portfolio
    portfolio_assets = crud.get_portfolio_assets_by_portfolio(db, portfolio_id)

    total_value = 0.0
    assets_data = []

    # Para cada ativo, busca preço atual e calcula valor
    for p_asset in portfolio_assets:
        asset = p_asset.asset
        current_price = get_current_price(asset.ticker)

        if current_price is None:
            current_price = 0.0

        current_value = p_asset.quantity * current_price
        total_value += current_value

        assets_data.append({
            "portfolio_asset_id": p_asset.id,
            "asset_id": asset.id,
            "asset_name": asset.name,
            "ticker": asset.ticker,
            "asset_class_name": asset.asset_class.name,
            "quantity": p_asset.quantity,
            "current_price": current_price,
            "current_value": current_value,
            "target_percentage": p_asset.target_percentage,
            "rebalance_threshold": p_asset.rebalance_threshold_percentage
        })

    # Calcula percentuais atuais
    for asset_data in assets_data:
        if total_value > 0:
            asset_data["current_percentage"] = (asset_data["current_value"] / total_value) * 100
        else:
            asset_data["current_percentage"] = 0.0

    # Gera alertas de rebalanceamento
    alerts = generate_rebalance_alerts(assets_data)

    return {
        "portfolio_id": portfolio_id,
        "total_value": total_value,
        "assets": assets_data,
        "rebalance_alerts": alerts
    }

def generate_rebalance_alerts(assets_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Gera alertas quando ativos desviam da alocação alvo.

    Args:
        assets_data: Lista com dados dos ativos e suas métricas

    Returns:
        list: Lista de alertas de rebalanceamento
    """
    alerts = []

    for asset in assets_data:
        current_pct = asset["current_percentage"]
        target_pct = asset["target_percentage"]
        threshold = asset["rebalance_threshold"]

        # Se não há meta definida, ignora
        if target_pct == 0 or threshold == 0:
            continue

        # Calcula desvio absoluto
        deviation = abs(current_pct - target_pct)

        # Se desvio ultrapassa o threshold, gera alerta
        if deviation > threshold:
            if current_pct > target_pct:
                action = f"Reduzir alocação (vender)"
                status = "Acima da meta"
            else:
                action = f"Aumentar alocação (comprar)"
                status = "Abaixo da meta"

            alerts.append({
                "asset_name": asset["asset_name"],
                "ticker": asset["ticker"],
                "current_pct": f"{current_pct:.2f}%",
                "target_pct": f"{target_pct:.2f}%",
                "deviation": f"{deviation:.2f}%",
                "status": status,
                "action": action
            })

    return alerts
