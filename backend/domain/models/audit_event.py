import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from infrastructure.db.session import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # Nullable for unauthenticated/system actions
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False, index=True) # CASE_ASSIGNED, TRIAGE_OVERRIDE, LOCATION_VERIFIED, EVIDENCE_ACCESSED, DISPUTE_DECISION
    resource_type = Column(String(50), nullable=False, index=True) # case, evidence, official_location, user, safety_report
    resource_id = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json = Column(JSONB, nullable=True)
