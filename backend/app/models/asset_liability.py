from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from app.database import Base

class AssetLiability(Base):
    __tablename__ = "assets_liabilities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ASSET, LIABILITY
    category = Column(String, nullable=False)  # e.g., REAL_ESTATE, VEHICLE, HOME_LOAN, PERSONAL_LOAN
    value = Column(Numeric(12, 2), nullable=False)
    as_of_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
