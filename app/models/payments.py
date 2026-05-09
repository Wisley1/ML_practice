from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
from sqlalchemy.schema import ForeignKey
from sqlalchemy import JSON

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    provider = Column(String, index=True)
    external_id = Column(String, index=True)
    amount_money = Column(Integer)
    credits_to_add = Column(Integer)
    status = Column(String, index=True)
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)