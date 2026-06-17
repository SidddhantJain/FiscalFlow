from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.category import Category

class BudgetBase(BaseModel):
    category_id: int
    amount: Decimal
    spent: Decimal = Decimal("0.00")
    start_date: date
    end_date: date

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    category_id: int | None = None
    amount: Decimal | None = None
    spent: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None

class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    category: Category | None = None

    model_config = ConfigDict(from_attributes=True)
