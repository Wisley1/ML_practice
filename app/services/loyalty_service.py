from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.loyalty_tiers import LoyaltyTier
from app.models.prediction_jobs import PredictionJob
from app.models.user_loyalty_state import UserLoyaltyState
from app.schemas.user import LoyaltyStatusOut


def default_loyalty_tier(db: Session) -> LoyaltyTier:
    ensure_loyalty_tiers_seeded(db)
    tier = db.scalars(
        select(LoyaltyTier).where(LoyaltyTier.is_active.is_(True)).order_by(LoyaltyTier.priority.asc())
    ).first()
    if tier is None:
        raise RuntimeError("Loyalty tiers not available")
    return tier


def ensure_user_loyalty_state(db: Session, user_id: int) -> tuple[UserLoyaltyState, bool]:
    ensure_loyalty_tiers_seeded(db)
    state = db.get(UserLoyaltyState, user_id)
    if state is None:
        t = default_loyalty_tier(db)
        state = UserLoyaltyState(
            user_id=user_id,
            current_tier_id=t.id,
            predictions_count_period=0,
        )
        db.add(state)
        db.flush()
        return state, True
    if state.current_tier_id is None:
        state.current_tier_id = default_loyalty_tier(db).id
        db.flush()
        return state, True
    return state, False


def ensure_loyalty_tiers_seeded(db: Session) -> None:
    if db.scalars(select(LoyaltyTier).limit(1)).first() is not None:
        return
    db.add_all(
        [
            LoyaltyTier(
                name="bronze",
                min_predictions_monthly=0,
                discount_percentage=0,
                priority=0,
                is_active=True,
                description="Bronze",
            ),
            LoyaltyTier(
                name="silver",
                min_predictions_monthly=10,
                discount_percentage=5,
                priority=1,
                is_active=True,
                description="Silver",
            ),
            LoyaltyTier(
                name="gold",
                min_predictions_monthly=50,
                discount_percentage=10,
                priority=2,
                is_active=True,
                description="Gold",
            ),
        ]
    )
    db.flush()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_month_start_naive() -> datetime:
    now = _utc_now()
    return datetime(now.year, now.month, 1, 0, 0, 0)


def completed_predictions_last_utc_days(db: Session, user_id: int, days: int = 30) -> int:
    """Matches admin metric: completed jobs since now-30d in naive UTC (same as prediction_jobs timestamps)."""
    since = _utc_now().replace(tzinfo=None) - timedelta(days=days)
    n = db.scalar(
        select(func.count())
        .select_from(PredictionJob)
        .where(
            PredictionJob.user_id == user_id,
            PredictionJob.status == "completed",
            PredictionJob.updated_at >= since,
        )
    )
    return int(n or 0)


def completed_predictions_this_utc_month(db: Session, user_id: int) -> int:
    start = _utc_month_start_naive()
    n = db.scalar(
        select(func.count())
        .select_from(PredictionJob)
        .where(
            PredictionJob.user_id == user_id,
            PredictionJob.status == "completed",
            PredictionJob.updated_at >= start,
        )
    )
    return int(n or 0)


def pick_tier_for_count(db: Session, count: int) -> LoyaltyTier | None:
    tiers = db.scalars(
        select(LoyaltyTier)
        .where(LoyaltyTier.is_active.is_(True))
        .order_by(
            LoyaltyTier.min_predictions_monthly.desc(),
            LoyaltyTier.priority.desc(),
        )
    ).all()
    for tier in tiers:
        threshold = tier.min_predictions_monthly or 0
        if count >= threshold:
            return tier
    return None


def sync_tier_from_period_count(db: Session, state: UserLoyaltyState) -> None:
    month_n = completed_predictions_this_utc_month(db, state.user_id)
    rolling_n = completed_predictions_last_utc_days(db, state.user_id, 30)
    stored = state.predictions_count_period or 0
    # Use the same horizon as the admin "last 30 days" column so tier matches what operators see.
    count = max(month_n, stored, rolling_n)
    if month_n > stored:
        state.predictions_count_period = month_n
    if count == 0:
        return
    new_tier = pick_tier_for_count(db, count)
    state.current_tier_id = new_tier.id if new_tier is not None else None


def recompute_user_loyalty(db: Session, user_id: int) -> None:
    state = db.get(UserLoyaltyState, user_id)
    if state is None:
        return
    count = state.predictions_count_period or 0
    new_tier = pick_tier_for_count(db, count)
    state.current_tier_id = new_tier.id if new_tier is not None else None
    state.predictions_count_period = 0


def recompute_all_users_loyalty(db: Session) -> None:
    for state in db.scalars(select(UserLoyaltyState)):
        count = state.predictions_count_period or 0
        new_tier = pick_tier_for_count(db, count)
        state.current_tier_id = new_tier.id if new_tier is not None else None
        state.predictions_count_period = 0
    db.commit()


def loyalty_status_for_user(db: Session, user_id: int) -> LoyaltyStatusOut:
    state, mutated = ensure_user_loyalty_state(db, user_id)
    if mutated:
        db.commit()
    db.refresh(state)
    before_tier = state.current_tier_id
    before_period = state.predictions_count_period
    sync_tier_from_period_count(db, state)
    if (
        state.current_tier_id != before_tier
        or state.predictions_count_period != before_period
        or mutated
    ):
        db.commit()
        db.refresh(state)
    tier_name: str | None = None
    discount_pct: int | None = None
    tier = db.get(LoyaltyTier, state.current_tier_id) if state.current_tier_id is not None else None
    if tier is not None:
        tier_name = tier.name
        if tier.discount_percentage is not None:
            discount_pct = int(tier.discount_percentage)
    return LoyaltyStatusOut(
        tier_name=tier_name,
        discount_percentage=discount_pct,
    )
