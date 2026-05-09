from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.prediction_jobs import PredictionJob
from app.models.user import User
from app.schemas.prediction import PredictionOut, PredictionRequestBody
from app.schemas.user import LoyaltyStatusOut
from app.services.loyalty_service import loyalty_status_for_user
from app.services.prediction_service import create_queued_prediction_job
from app.tasks.prediction_tasks import run_prediction_task

router = APIRouter()


def _job_to_out(job: PredictionJob, loyalty: LoyaltyStatusOut | None = None) -> PredictionOut:
    return PredictionOut(
        id=job.id,
        status=job.status,
        model_id=job.model_id,
        result=job.result,
        error_message=job.error_message,
        idempotency_key=job.idempotency_key or "",
        credits_charged=None,
        loyalty=loyalty,
    )


@router.get("/{job_id}", response_model=PredictionOut)
def get_prediction(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(PredictionJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    loyalty = (
        loyalty_status_for_user(db, current_user.id) if job.status == "completed" else None
    )
    return _job_to_out(job, loyalty=loyalty)


@router.post(
    "",
    response_model=PredictionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_prediction(
    body: PredictionRequestBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    job = create_queued_prediction_job(
        db,
        current_user.id,
        body.model_id,
        body.text,
        idempotency_key,
    )
    if job.status == "queued":
        run_prediction_task.delay(job.id)
    loyalty = (
        loyalty_status_for_user(db, current_user.id) if job.status == "completed" else None
    )
    return _job_to_out(job, loyalty=loyalty)
