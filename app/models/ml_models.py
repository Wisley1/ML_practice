from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
from sqlalchemy.schema import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import Boolean

class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String, index=True)
    description = Column(String, index=True)
    model_type = Column(String, index=True)
    storage_path = Column(String, index=True)
    cost_credits_base = Column(Integer)
    extra_metadata = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)