from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.category import Category
from app.schemas.account import Account

class TransactionBase(BaseModel):
    date: date
    description: str
    amount: Decimal
    type: str  # INCOME, EXPENSE, SAVINGS, INVESTMENT, TRANSFER, LOAN, TAX
    category_id: int | None = None
    account_id: int
    destination_account_id: int | None = None
    reference_number: str | None = None
    is_recurring: bool = False
    notes: str | None = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    type: str | None = None
    category_id: int | None = None
    account_id: int | None = None
    destination_account_id: int | None = None
    reference_number: str | None = None
    is_recurring: bool | None = None
    notes: str | None = None

class Transaction(TransactionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # Avoid circular dependency by typing nested relations or lazy loading
    # We can keep them optional or just refer to schemas
    category: Category | None = None
    # We will resolve account models dynamically or using standard Account schemas
    
    model_config = ConfigDict(from_attributes=True)
