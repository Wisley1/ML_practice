from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.wallet import WalletOut
from app.services.wallet_service import get_wallet_balance

router = APIRouter()


@router.get("/me", response_model=WalletOut)
def wallet_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance_credits = get_wallet_balance(db, current_user.id)
    return WalletOut(user_id=current_user.id, balance_credits=balance_credits)
