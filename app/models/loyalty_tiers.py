from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base


class LoyaltyTier(Base):
    __tablename__ = "loyalty_tiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    min_predictions_monthly = Column(Integer)
    discount_percentage = Column(Integer)
    priority = Column(Integer)
    is_active = Column(Boolean, default=True)
    description = Column(String, index=True)
