import os

from fastapi import HTTPException, status
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.loyalty_tiers import LoyaltyTier
from app.models.user import User
from app.models.user_loyalty_state import UserLoyaltyState
from app.models.wallet import Wallet
from app.schemas.auth import Token
from app.services.loyalty_service import default_loyalty_tier
from core.config import settings
from core.security import create_access_token, hash_password, verify_password


def _bootstrap_admin_emails() -> set[str]:
    raw = (
        os.environ.get("ADMIN_BOOTSTRAP_EMAILS", "").strip()
        or (settings.admin_bootstrap_emails or "").strip()
    )
    if not raw:
        return set()
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def get_default_tier(db: Session) -> LoyaltyTier:
    try:
        return default_loyalty_tier(db)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Loyalty tiers not available",
        )


def register_user(db: Session, email: EmailStr, password: str) -> User:
    email_norm = str(email).strip().lower()
    existing = db.scalars(select(User).where(func.lower(User.email) == email_norm)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = "admin" if email_norm in _bootstrap_admin_emails() else "user"
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(Wallet(user_id=user.id, balance_credits=0))

    tier = get_default_tier(db)
    db.add(
        UserLoyaltyState(
            user_id=user.id,
            current_tier_id=tier.id,
            predictions_count_period=0,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: EmailStr, password: str) -> Token:
    email_norm = str(email).strip().lower()
    user = db.scalars(select(User).where(func.lower(User.email) == email_norm)).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if email_norm in _bootstrap_admin_emails() and user.role != "admin":
        user.role = "admin"
        db.commit()
        db.refresh(user)
    token = create_access_token(str(user.id), user.role)
    return Token(access_token=token)
