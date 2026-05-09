from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ledger_entries import LedgerEntry
from app.models.wallet import Wallet


def get_wallet_balance(db: Session, user_id: int) -> int:
    wallet = db.get(Wallet, user_id)
    if wallet is None:
        return 0
    return wallet.balance_credits or 0


def apply_ledger_entry(
    db: Session,
    user_id: int,
    amount: int,
    entry_type: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> LedgerEntry:
    if amount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount cannot be zero",
        )

    wallet = db.scalars(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    ).one_or_none()
    if wallet is None:
        db.add(Wallet(user_id=user_id, balance_credits=0))
        db.flush()
        wallet = db.scalars(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        ).one()

    balance = wallet.balance_credits or 0
    new_balance = balance + amount
    if new_balance < 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits",
        )

    entry = LedgerEntry(
        user_id=user_id,
        amount=amount,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(entry)
    wallet.balance_credits = new_balance
    db.commit()
    db.refresh(entry)
    return entry
