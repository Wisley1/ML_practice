from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import MockTopUpBody, MockTopUpResponse
from app.services.payment_service import process_mock_topup

router = APIRouter()


@router.post("/mock-topup", response_model=MockTopUpResponse)
def mock_topup(
    body: MockTopUpBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment_id, balance_credits = process_mock_topup(db, current_user.id, body.credits_to_add)
    return MockTopUpResponse(payment_id=payment_id, balance_credits=balance_credits)
