from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base, utc_now

class StatementFile(Base):
    __tablename__ = "statement_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    saved_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    bank_type = Column(String, nullable=False, default="AXIS_CSV")
    transaction_count = Column(Integer, nullable=False, default=0)
    upload_date = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
    account = relationship("Account")
