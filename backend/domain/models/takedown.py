from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.db.session import Base

class TakedownPolicy(Base):
    __tablename__ = "takedown_policies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String, index=True, nullable=False)
    target = Column(String, nullable=False)
    target_type = Column(String, nullable=False) # e.g. "phone", "upi", "bank", "url"
    action = Column(String, nullable=False) # e.g. "freeze_account"
    reason = Column(Text, nullable=False)
    
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
