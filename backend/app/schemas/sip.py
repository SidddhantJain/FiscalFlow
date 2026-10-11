from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime

class SipScheduleBase(BaseModel):
    scheme_name: str
    asset_class: str = "MUTUAL_FUND"  # MUTUAL_FUND, STOCK, ELSS, INDEX_FUND, ETF
    amount: Decimal
    frequency: str = "MONTHLY"
    sip_day_of_month: int = 5
    start_date: date = date.today()
    next_sip_date: date | None = None
    broker: str = "Groww"  # Groww, Angel One, Zerodha, etc.
    folio_number: str | None = None
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED
    account_id: int | None = None
    notes: str | None = None

class SipScheduleCreate(SipScheduleBase):
    pass

class SipScheduleUpdate(BaseModel):
    scheme_name: str | None = None
    asset_class: str | None = None
    amount: Decimal | None = None
    frequency: str | None = None
    sip_day_of_month: int | None = None
    next_sip_date: date | None = None
    broker: str | None = None
    folio_number: str | None = None
    status: str | None = None
    account_id: int | None = None
    notes: str | None = None

class SipSchedule(SipScheduleBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
