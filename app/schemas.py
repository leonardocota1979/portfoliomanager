# app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# ============================================================================
# SCHEMAS DE USUÁRIOS
# ============================================================================

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None

class UserResetPassword(BaseModel):
    password: str

# ============================================================================
# SCHEMAS DE PORTFOLIOS
# ============================================================================

class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    total_value: float = 0.0
    currency: str = "USD"

class PortfolioCreate(PortfolioBase):
    pass

class Portfolio(PortfolioBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SCHEMAS DE GLOBAL ASSET CLASSES
# ============================================================================

class GlobalAssetClassBase(BaseModel):
    name: str
    description: Optional[str] = None

class GlobalAssetClassCreate(GlobalAssetClassBase):
    pass

class GlobalAssetClass(GlobalAssetClassBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SCHEMAS DE ASSET CLASSES
# ============================================================================

class AssetClassBase(BaseModel):
    name: str
    target_percentage: float = 0.0
    rebalance_threshold_percentage: float = 5.0

class AssetClassCreate(AssetClassBase):
    is_custom: bool = False

class AssetClassUpdate(BaseModel):
    name: Optional[str] = None
    target_percentage: Optional[float] = None
    rebalance_threshold_percentage: Optional[float] = None

class AssetClass(AssetClassBase):
    id: int
    portfolio_id: int
    is_custom: bool = False
    pending_approval: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SCHEMAS DE ASSETS
# ============================================================================

class AssetBase(BaseModel):
    name: str
    ticker: str
    source: str = "manual"

class AssetCreate(AssetBase):
    asset_class_id: int

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    ticker: Optional[str] = None

class Asset(AssetBase):
    id: int
    asset_class_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SCHEMAS DE PORTFOLIO ASSETS
# ============================================================================

class PortfolioAssetBase(BaseModel):
    quantity: float = 0.0
    target_percentage: float = 0.0
    rebalance_threshold_percentage: float = 5.0

class PortfolioAssetCreate(PortfolioAssetBase):
    asset_id: int

class PortfolioAssetUpdate(BaseModel):
    quantity: Optional[float] = None
    target_percentage: Optional[float] = None
    rebalance_threshold_percentage: Optional[float] = None

class PortfolioAsset(PortfolioAssetBase):
    id: int
    portfolio_id: int
    asset_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SCHEMAS DE DASHBOARD
# ============================================================================

class DashboardAssetData(BaseModel):
    id: int
    name: str
    ticker: str
    asset_class_name: str
    quantity: float
    current_price: float
    current_value: float
    current_percentage: float
    target_percentage: float
    rebalance_threshold_percentage: float
    deviation_percentage: float
    rebalance_status: str
    rebalance_emoji: str
    rebalance_color_class: str
    units_to_rebalance: float

    class Config:
        from_attributes = True

class DashboardResponse(BaseModel):
    portfolio_id: int
    portfolio_name: str
    total_portfolio_value: float
    assets_data: List[DashboardAssetData]
    alerts: List[str] = []
