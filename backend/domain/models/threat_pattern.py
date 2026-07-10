import uuid
from datetime import datetime, timezone, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from infrastructure.db.session import Base


class ThreatPattern(Base):
    """
    Threat Pattern Repository (TPR) — the versioned ontology of known scam types.
    Supports lifecycle states (active, deprecated) and versioning per ADR-004.
    """
    __tablename__ = "threat_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Classification code — e.g. "FIN-PAY-UPI", "SOC-IMP-DA"
    code = Column(String, unique=True, nullable=False, index=True)
    
    # Human-readable name and description
    pattern_signature = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    severity_score = Column(Float, nullable=False)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))  # e.g. "Financial", "Social Engineering"
    subcategory = Column(String, nullable=True)  # e.g. "Payment Fraud", "Impersonation"
    
    # Ontology versioning
    ontology_version = Column(String, default="1.0", nullable=False)
    
    # AI matching metadata
    keywords = Column(JSONB, nullable=True)  # List of keywords that trigger this pattern
    sample_prompts = Column(JSONB, nullable=True)  # Sample texts for vector embedding
    
    # Lifecycle
    is_active = Column(Boolean, default=True)
    deprecated_flag = Column(Boolean, default=False)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
