from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
from sqlalchemy.schema import ForeignKey
from sqlalchemy import JSON
class PredictionJob(Base):
    __tablename__ = "prediction_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    status = Column(String, index=True)
    input_text = Column(String, index=True)
    result = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    idempotency_key = Column(String, index=True)
    model_id = Column(Integer, ForeignKey("ml_models.id"), index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)