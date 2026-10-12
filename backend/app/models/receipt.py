from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base, utc_now

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String, nullable=False)
    ocr_raw_text = Column(Text, nullable=True)
    merchant_name = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="receipts")
