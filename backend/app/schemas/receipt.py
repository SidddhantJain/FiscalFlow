from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime

class ReceiptBase(BaseModel):
    transaction_id: int | None = None
    file_path: str
    ocr_raw_text: str | None = None
    merchant_name: str | None = None
    date: date | None = None
    amount: Decimal | None = None

class ReceiptCreate(ReceiptBase):
    pass

class ReceiptUpdate(BaseModel):
    transaction_id: int | None = None
    file_path: str | None = None
    ocr_raw_text: str | None = None
    merchant_name: str | None = None
    date: date | None = None
    amount: Decimal | None = None

class Receipt(ReceiptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
