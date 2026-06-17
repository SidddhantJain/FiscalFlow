from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.account import Account

class SubscriptionBase(BaseModel):
    account_id: int | None = None
    name: str
    amount: Decimal
    billing_cycle: str = "MONTHLY"  # MONTHLY, ANNUAL
    next_renewal_date: date
    is_active: bool = True

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    account_id: int | None = None
    name: str | None = None
    amount: Decimal | None = None
    billing_cycle: str | None = None
    next_renewal_date: date | None = None
    is_active: bool | None = None

class Subscription(SubscriptionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    account: Account | None = None

    model_config = ConfigDict(from_attributes=True)
