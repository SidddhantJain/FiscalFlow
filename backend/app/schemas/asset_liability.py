from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime

class AssetLiabilityBase(BaseModel):
    name: str
    type: str  # ASSET, LIABILITY
    category: str  # e.g., REAL_ESTATE, VEHICLE, HOME_LOAN, PERSONAL_LOAN
    value: Decimal
    as_of_date: date

class AssetLiabilityCreate(AssetLiabilityBase):
    pass

class AssetLiabilityUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    category: str | None = None
    value: Decimal | None = None
    as_of_date: date | None = None

class AssetLiability(AssetLiabilityBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
