from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.loyalty_tiers import LoyaltyTier
from app.models.prediction_jobs import PredictionJob
from app.models.user import User
from app.models.user_loyalty_state import UserLoyaltyState
from app.models.wallet import Wallet
from app.schemas.admin import AdminUserRow
from app.services.loyalty_service import ensure_user_loyalty_state, sync_tier_from_period_count


def list_users_for_admin(db: Session) -> list[AdminUserRow]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

    count_stmt = (
        select(PredictionJob.user_id, func.count(PredictionJob.id).label("n"))
        .where(PredictionJob.status == "completed", PredictionJob.updated_at >= since)
        .group_by(PredictionJob.user_id)
    )
    pred_map: dict[int, int] = {uid: int(n) for uid, n in db.execute(count_stmt).all()}

    users = db.scalars(select(User).order_by(User.id.asc())).all()
    mutated_loyalty = False
    for u in users:
        st, created = ensure_user_loyalty_state(db, u.id)
        before_tier = st.current_tier_id
        before_period = st.predictions_count_period
        sync_tier_from_period_count(db, st)
        if (
            created
            or st.current_tier_id != before_tier
            or st.predictions_count_period != before_period
        ):
            mutated_loyalty = True
    if mutated_loyalty:
        db.commit()

    rows: list[AdminUserRow] = []
    for u in users:
        wallet = db.get(Wallet, u.id)
        balance = wallet.balance_credits if wallet is not None else 0
        tier_name: str | None = None
        ls = db.get(UserLoyaltyState, u.id)
        if ls is not None and ls.current_tier_id is not None:
            lt = db.get(LoyaltyTier, ls.current_tier_id)
            tier_name = lt.name if lt is not None else None
        rows.append(
            AdminUserRow(
                id=u.id,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                tier_name=tier_name,
                balance_credits=int(balance or 0),
                predictions_completed_last_30_days=pred_map.get(u.id, 0),
            )
        )
    return rows
