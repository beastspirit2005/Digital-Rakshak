import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from infrastructure.db.session import Base
import enum


class EvidenceType(str, enum.Enum):
    SCREENSHOT = "screenshot"
    AUDIO = "audio"
    PDF = "pdf"
    RAW_TEXT = "raw_text"
    URL = "url"
    SMS = "sms"
    EMAIL_CONTENT = "email_content"
    TRANSACTION_RECEIPT = "transaction_receipt"
    APK = "apk"


class Evidence(Base):
    """
    Raw Evidence is IMMUTABLE. Once ingested, it is never modified.
    Derived intelligence (extracted entities, Attack DNA) lives separately.
    """
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    
    # What kind of evidence
    evidence_type = Column(String, nullable=False)  # EvidenceType value
    
    # Content — raw text stored directly, files stored as path/URL
    content_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)  # For binary uploads (screenshots, audio, PDFs)
    file_hash_sha256 = Column(String(64), nullable=True, index=True) # Chain of Custody hash
    
    # Metadata extracted by AI (immutable snapshot at time of ingestion)
    extracted_metadata = Column(JSONB, nullable=True)
    
    # Source tracking
    source = Column(String, nullable=True)  # e.g. "citizen_upload", "api_ingest", "scrape"
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # Relationships
    case = relationship("Case", back_populates="evidence")
