from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime

class InvestmentBase(BaseModel):
    name: str
    symbol: str | None = None
    asset_class: str = "STOCK"  # MUTUAL_FUND, STOCK, GOLD, FD, PPF, NPS, ELSS, ETF
    account_id: int | None = None
    broker: str | None = None
    units: Decimal | None = None
    purchase_price: Decimal
    current_value: Decimal
    buy_date: datetime | None = None

class InvestmentCreate(InvestmentBase):
    pass

class InvestmentUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    account_id: int | None = None
    broker: str | None = None
    units: Decimal | None = None
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    buy_date: datetime | None = None
    last_updated: datetime | None = None

class Investment(InvestmentBase):
    id: int
    user_id: int
    last_updated: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
