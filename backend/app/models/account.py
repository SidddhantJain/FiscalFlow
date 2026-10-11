from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    bank_name = Column(String, nullable=True)
    account_type = Column(String, nullable=False)  # SAVINGS, SALARY, CURRENT, DEMAT, CREDIT_CARD, WALLET, CASH, INVESTMENT
    account_number = Column(String, nullable=True)  # Bank A/c No or Demat Client ID
    opening_balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    current_balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    
    transactions = relationship(
        "Transaction",
        foreign_keys="[Transaction.account_id]",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    destination_transactions = relationship(
        "Transaction",
        foreign_keys="[Transaction.destination_account_id]",
        back_populates="destination_account",
        cascade="all, delete-orphan"
    )
    
    subscriptions = relationship("Subscription", back_populates="account", cascade="all, delete-orphan")
