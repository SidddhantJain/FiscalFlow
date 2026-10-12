from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean
from app.database import Base, utc_now

class FinancialYear(Base):
    __tablename__ = "financial_years"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True, index=True, nullable=False)  # e.g., "FY 2024-25"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
