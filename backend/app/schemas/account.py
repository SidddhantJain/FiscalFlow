from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime

class AccountBase(BaseModel):
    name: str
    bank_name: str | None = None
    account_type: str  # SAVINGS, SALARY, CREDIT_CARD, WALLET, CASH, INVESTMENT
    opening_balance: Decimal = Decimal("0.00")
    currency: str = "INR"

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: str | None = None
    bank_name: str | None = None
    account_type: str | None = None
    opening_balance: Decimal | None = None
    current_balance: Decimal | None = None
    currency: str | None = None

class Account(AccountBase):
    id: int
    user_id: int
    current_balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
