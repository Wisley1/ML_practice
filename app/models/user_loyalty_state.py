from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class UserLoyaltyState(Base):
    __tablename__ = "user_loyalty_states"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    current_tier_id = Column(Integer, ForeignKey("loyalty_tiers.id"), index=True, nullable=True)
    predictions_count_period = Column(Integer, default=0)
