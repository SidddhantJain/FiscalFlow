from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.database import Base

class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=True)  # Stock ticker or fund code (e.g. TCS, INFY, PPFAS)
    asset_class = Column(String, nullable=False)  # MUTUAL_FUND, STOCK, GOLD, FD, PPF, NPS, ELSS, ETF
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    broker = Column(String, nullable=True)  # Groww, Angel One, Zerodha, etc.
    units = Column(Numeric(16, 4), nullable=True)  # Shares or MF Units
    purchase_price = Column(Numeric(12, 2), nullable=False)  # Avg purchase price per unit
    current_value = Column(Numeric(12, 2), nullable=False)  # Current total value
    buy_date = Column(DateTime, nullable=True)  # Purchase or SIP date
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
