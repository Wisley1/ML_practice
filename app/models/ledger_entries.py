from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
from sqlalchemy.schema import ForeignKey

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Integer)
    entry_type = Column(String, index=True)
    reference_type = Column(String, index=True)
    reference_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.now)