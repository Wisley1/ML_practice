from sqlalchemy.orm import Session

from app.models.payments import Payment
from app.services.wallet_service import apply_ledger_entry, get_wallet_balance


def process_mock_topup(db: Session, user_id: int, credits_to_add: int) -> tuple[int, int]:
    payment = Payment(
        user_id=user_id,
        provider="mock",
        external_id=None,
        amount_money=0,
        credits_to_add=credits_to_add,
        status="completed",
        raw_payload=None,
    )
    db.add(payment)
    db.flush()

    apply_ledger_entry(
        db,
        user_id,
        credits_to_add,
        "topup",
        reference_type="payment",
        reference_id=payment.id,
    )
    balance_credits = get_wallet_balance(db, user_id)
    return payment.id, balance_credits
