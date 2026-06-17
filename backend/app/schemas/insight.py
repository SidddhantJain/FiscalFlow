from pydantic import BaseModel, ConfigDict
from datetime import datetime

class InsightBase(BaseModel):
    type: str  # LEAK, FORECAST, BUDGET_WARNING, GENERAL
    title: str
    content: str
    severity: str = "INFO"  # INFO, WARNING, CRITICAL
    is_read: bool = False

class InsightCreate(InsightBase):
    pass

class InsightUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    content: str | None = None
    severity: str | None = None
    is_read: bool | None = None

class Insight(InsightBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
