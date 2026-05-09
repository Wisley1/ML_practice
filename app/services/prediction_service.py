from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.dispatch import predict_with_model

from app.db.session import SessionLocal
from app.models.ml_models import MLModel
from app.models.prediction_jobs import PredictionJob
from app.services.loyalty_service import ensure_user_loyalty_state, sync_tier_from_period_count
from app.services.pricing_service import get_effective_cost
from app.services.wallet_service import apply_ledger_entry, get_wallet_balance


def create_queued_prediction_job(
    db: Session,
    user_id: int,
    model_id: int,
    input_text: str,
    idempotency_key: str | None,
) -> PredictionJob:
    key = (idempotency_key or "").strip() or None

    if key is not None:
        existing = db.scalars(
            select(PredictionJob).where(
                PredictionJob.user_id == user_id,
                PredictionJob.idempotency_key == key,
            )
        ).first()
        if existing is not None:
            return existing

    model = db.get(MLModel, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    if not model.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model inactive")

    cost = get_effective_cost(db, user_id, model)
    if get_wallet_balance(db, user_id) < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits",
        )

    now = datetime.now(timezone.utc)
    job = PredictionJob(
        user_id=user_id,
        model_id=model_id,
        input_text=input_text,
        status="queued",
        idempotency_key=key or "",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def execute_prediction_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.scalars(
            select(PredictionJob).where(PredictionJob.id == job_id).with_for_update()
        ).first()
        if job is None:
            db.commit()
            return
        if job.status != "queued":
            db.commit()
            return

        model = db.get(MLModel, job.model_id)
        if model is None or not model.is_active:
            job.status = "failed"
            job.error_message = "Model not found or inactive"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            return

        cost = get_effective_cost(db, job.user_id, model)
        if get_wallet_balance(db, job.user_id) < cost:
            job.status = "failed"
            job.error_message = "Insufficient credits"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        db.flush()

        try:
            result = predict_with_model(model, job.input_text)
            job.result = result
            job.status = "completed"
            job.error_message = None
            job.updated_at = datetime.now(timezone.utc)
            db.flush()
            loyalty_state, _ = ensure_user_loyalty_state(db, job.user_id)
            loyalty_state.predictions_count_period = (
                (loyalty_state.predictions_count_period or 0) + 1
            )
            sync_tier_from_period_count(db, loyalty_state)
            db.flush()
            if cost > 0:
                apply_ledger_entry(
                    db,
                    job.user_id,
                    -cost,
                    "prediction_charge",
                    reference_type="prediction_job",
                    reference_id=job.id,
                )
            else:
                db.commit()
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
