from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base, utc_now

class UserTagRule(Base):
    __tablename__ = "user_tag_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pattern = Column(String, nullable=False, index=True)  # merchant or keyword (case-insensitive)
    tags = Column(String, nullable=False)                 # Comma-separated tags (e.g. "Food, Cafe")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    match_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
    category = relationship("Category")
