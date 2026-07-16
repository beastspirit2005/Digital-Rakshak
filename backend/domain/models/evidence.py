import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
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
    QR = "qr"


class Evidence(Base):
    """
    Raw Evidence is IMMUTABLE. Once ingested, it is never modified.
    Derived intelligence (extracted entities, Attack DNA) lives separately.
    """
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    
    # What kind of evidence
    evidence_type = Column(String, nullable=False)  # EvidenceType value
    
    # Content — raw text stored directly, files stored as path/URL
    content_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)  # For binary uploads (screenshots, audio, PDFs)
    file_hash_sha256 = Column(String(64), nullable=True, index=True) # Chain of Custody hash
    
    # EVR Forensic & Legally Traceable Attributes
    sha256 = Column(String(64), nullable=True, index=True)  # Primary cryptographic SHA256 digest
    mime_type = Column(String, nullable=True)
    storage_location = Column(String, nullable=True)  # Disk or S3/Blob URI
    file_size_bytes = Column(Integer, nullable=True)
    evidence_owner = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    integrity_status = Column(String, default="VERIFIED", nullable=False)  # VERIFIED, TAMPERED, PENDING, ARCHIVED
    
    # Metadata extracted by AI (immutable snapshot at time of ingestion)
    extracted_metadata = Column(JSONB, nullable=True)
    
    # Source tracking
    source = Column(String, nullable=True)  # e.g. "citizen_upload", "api_ingest", "scrape"
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # Relationships
    case = relationship("Case", back_populates="evidence")
    coc_logs = relationship("ChainOfCustodyLog", back_populates="evidence", lazy="selectin", cascade="all, delete-orphan")


class ChainOfCustodyLog(Base):
    """
    Append-only legal audit trail tracking every lifecycle stage of Evidence:
    Uploaded -> AI Access -> Human Review -> Verified -> Archived.
    """
    __tablename__ = "chain_of_custody"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False, index=True)
    
    actor = Column(String, nullable=False)   # e.g. "Citizen (Submitter)", "AI: OCRAnalysisAgent", "Inv. Rajesh"
    action = Column(String, nullable=False)  # e.g. "UPLOADED", "AI_ACCESS", "HUMAN_REVIEW", "VERIFIED", "ARCHIVED"
    remarks = Column(Text, nullable=True)    # e.g. "SHA-256 digest verified", "Extracted 142 tokens"
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    
    evidence = relationship("Evidence", back_populates="coc_logs")
