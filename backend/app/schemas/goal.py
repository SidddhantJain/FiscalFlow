from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime

class GoalBase(BaseModel):
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0.00")
    deadline: date | None = None
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, ABANDONED

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount: Decimal | None = None
    current_amount: Decimal | None = None
    deadline: date | None = None
    status: str | None = None

class Goal(GoalBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
