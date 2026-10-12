from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from app.database import Base, utc_now

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # LEAK, FORECAST, BUDGET_WARNING, GENERAL
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    severity = Column(String, default="INFO", nullable=False)  # INFO, WARNING, CRITICAL
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
