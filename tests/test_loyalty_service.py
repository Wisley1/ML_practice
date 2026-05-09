from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select

from app.models.loyalty_tiers import LoyaltyTier
from app.models.ml_models import MLModel
from app.models.prediction_jobs import PredictionJob
from app.models.user import User
from app.models.user_loyalty_state import UserLoyaltyState
from app.services import loyalty_service as loyalty_service_mod
from app.services.loyalty_service import pick_tier_for_count, sync_tier_from_period_count


def test_pick_tier_for_count_respects_thresholds(db_session):
    db_session.add_all(
        [
            LoyaltyTier(
                name="bronze",
                min_predictions_monthly=0,
                discount_percentage=0,
                priority=0,
                is_active=True,
                description="b",
            ),
            LoyaltyTier(
                name="silver",
                min_predictions_monthly=10,
                discount_percentage=5,
                priority=1,
                is_active=True,
                description="s",
            ),
            LoyaltyTier(
                name="gold",
                min_predictions_monthly=50,
                discount_percentage=10,
                priority=2,
                is_active=True,
                description="g",
            ),
        ]
    )
    db_session.commit()

    assert pick_tier_for_count(db_session, 0).name == "bronze"
    assert pick_tier_for_count(db_session, 15).name == "silver"
    assert pick_tier_for_count(db_session, 60).name == "gold"


def test_sync_tier_uses_same_30d_window_as_admin(db_session):
    """Tier must not stay bronze when period/month counters are 0 but last-30d completed count qualifies."""
    db_session.add_all(
        [
            LoyaltyTier(
                name="bronze",
                min_predictions_monthly=0,
                discount_percentage=0,
                priority=0,
                is_active=True,
                description="b",
            ),
            LoyaltyTier(
                name="silver",
                min_predictions_monthly=10,
                discount_percentage=5,
                priority=1,
                is_active=True,
                description="s",
            ),
        ]
    )
    db_session.flush()
    bronze = db_session.scalars(select(LoyaltyTier).where(LoyaltyTier.name == "bronze")).one()
    u = User(email="roll30@example.com", hashed_password="x", role="user")
    db_session.add(u)
    db_session.flush()
    m = MLModel(
        owner_id=None,
        name="m",
        description="",
        model_type="embeddings_sklearn",
        storage_path="",
        cost_credits_base=1,
        extra_metadata=None,
        is_active=True,
    )
    db_session.add(m)
    db_session.flush()
    db_session.add(
        UserLoyaltyState(
            user_id=u.id,
            current_tier_id=bronze.id,
            predictions_count_period=0,
        )
    )
    april = datetime(2026, 4, 15, 12, 0, 0)
    for i in range(11):
        db_session.add(
            PredictionJob(
                user_id=u.id,
                model_id=m.id,
                status="completed",
                input_text=f"t{i}",
                idempotency_key=f"k{i}",
                updated_at=april,
                created_at=april,
            )
        )
    db_session.commit()

    state = db_session.get(UserLoyaltyState, u.id)
    fixed_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    with patch.object(loyalty_service_mod, "_utc_now", return_value=fixed_now):
        sync_tier_from_period_count(db_session, state)
    db_session.commit()

    db_session.refresh(state)
    tier = db_session.get(LoyaltyTier, state.current_tier_id)
    assert tier is not None
    assert tier.name == "silver"
