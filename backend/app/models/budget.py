from sqlalchemy import Column, Integer, Numeric, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base, utc_now

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    spent = Column(Numeric(12, 2), default=0.00, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    name = Column(String, nullable=True)  # Optional custom budget line item name
    notes = Column(String, nullable=True) # Strategy & notes (e.g. "26 working days @ ₹100-150/day")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
