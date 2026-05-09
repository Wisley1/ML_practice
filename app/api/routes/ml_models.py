from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ml_models import MLModel
from app.schemas.ml_model_public import MLModelOut

router = APIRouter()


@router.get("", response_model=list[MLModelOut])
def list_models(db: Session = Depends(get_db)):
    rows = db.scalars(select(MLModel).where(MLModel.is_active.is_(True)).order_by(MLModel.id)).all()
    return rows
