from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.database import Base

class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    asset_class = Column(String, nullable=False)  # MUTUAL_FUND, STOCK, GOLD, FD, PPF, NPS
    units = Column(Numeric(16, 4), nullable=True)  # Optional for FD or Gold grams vs Stock shares
    purchase_price = Column(Numeric(12, 2), nullable=False)  # Price paid per unit, or initial value
    current_value = Column(Numeric(12, 2), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
