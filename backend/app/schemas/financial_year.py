from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class FinancialYearBase(BaseModel):
    label: str  # e.g., "FY 2024-25"
    start_date: date
    end_date: date
    is_locked: bool = False

class FinancialYearCreate(FinancialYearBase):
    pass

class FinancialYearUpdate(BaseModel):
    label: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_locked: bool | None = None

class FinancialYear(FinancialYearBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
