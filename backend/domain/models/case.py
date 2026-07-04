import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from infrastructure.db.session import Base
import enum


class CaseStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_number = Column(String, unique=True, index=True, nullable=False)
    
    # Submitter info
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Core content
    scam_text = Column(Text, nullable=False)
    scam_type_code = Column(String, nullable=True)  # e.g. "FIN-PAY-UPI"
    
    # Location
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # AI analysis results
    threat_confidence_score = Column(Float, nullable=True)
    ai_decision = Column(JSONB, nullable=True)  # Full AI Explainability Object
    
    # Advanced Intelligence
    attack_dna = Column(JSONB, nullable=True)
    timeline_events = Column(JSONB, nullable=True)
    # Note: semantic_embedding vector column and postgis geometry are handled in DB directly
    
    # Status tracking
    status = Column(String, default=CaseStatus.SUBMITTED.value, nullable=False)
    priority = Column(String, default=CasePriority.MEDIUM.value, nullable=False)
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Financial
    estimated_amount = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    evidence = relationship("Evidence", back_populates="case", lazy="selectin")
