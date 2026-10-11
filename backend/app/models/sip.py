from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class SipSchedule(Base):
    __tablename__ = "sip_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    scheme_name = Column(String, nullable=False)
    asset_class = Column(String, default="MUTUAL_FUND", nullable=False)  # MUTUAL_FUND, STOCK, ELSS, INDEX_FUND, ETF
    amount = Column(Numeric(12, 2), nullable=False)
    frequency = Column(String, default="MONTHLY", nullable=False)  # MONTHLY, WEEKLY, QUARTERLY
    sip_day_of_month = Column(Integer, default=5, nullable=False)  # e.g., 5, 10, 15
    start_date = Column(Date, default=date.today, nullable=False)
    next_sip_date = Column(Date, nullable=False)
    broker = Column(String, default="Groww", nullable=False)  # Groww, Angel One, Zerodha, etc.
    folio_number = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE, PAUSED, COMPLETED
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    account = relationship("Account")
