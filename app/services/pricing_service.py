from sqlalchemy.orm import Session

from app.models.loyalty_tiers import LoyaltyTier
from app.models.ml_models import MLModel
from app.models.user_loyalty_state import UserLoyaltyState


def get_effective_cost(db: Session, user_id: int, model: MLModel) -> int:
    base = model.cost_credits_base or 0
    discount_pct = 0
    state = db.get(UserLoyaltyState, user_id)
    if state is not None and state.current_tier_id is not None:
        tier = db.get(LoyaltyTier, state.current_tier_id)
        if tier is not None and tier.is_active and tier.discount_percentage is not None:
            discount_pct = max(0, min(100, int(tier.discount_percentage)))
    effective = base * (100 - discount_pct) // 100
    return max(0, effective)
