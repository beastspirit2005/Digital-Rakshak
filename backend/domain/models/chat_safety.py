import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from infrastructure.db.session import Base

class CaseMessage(Base):
    __tablename__ = "case_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    attachments = Column(JSONB, nullable=True)  # List of {url, filename, sha256, mime_type, file_size}
    moderation_flag = Column(String(50), default="clean", nullable=False, index=True)  # clean, warning_issued, blocked_credentials, flagged_scam
    scanner_rule = Column(String(100), nullable=True)
    is_redacted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    case = relationship("Case", foreign_keys=[case_id])
    sender = relationship("User", foreign_keys=[sender_id])


class SafetyReport(Base):
    __tablename__ = "safety_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    reported_message_id = Column(UUID(as_uuid=True), ForeignKey("case_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # payment_demand, credential_harvesting, harassment, impersonation, recovery_scam
    reason_narrative = Column(Text, nullable=False)
    status = Column(String(50), default="pending_review", nullable=False, index=True)  # pending_review, under_review, protective_action, resolved_closed
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decision = Column(String(64), nullable=True)  # no_violation, warning_issued, message_restricted, account_suspended, escalated_police
    decision_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    evidence_package = relationship("PreservedEvidencePackage", back_populates="report", uselist=False)


class PreservedEvidencePackage(Base):
    __tablename__ = "preserved_evidence_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("safety_reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    context_window_json = Column(JSONB, nullable=False)  # Immutable snapshot: {reported_msg, preceding_msgs, succeeding_msgs, captured_at}
    package_sha256 = Column(String(64), nullable=False, index=True)  # SHA-256 digest of canonical context_window_json
    retention_until = Column(DateTime(timezone=True), nullable=False)
    is_legal_hold = Column(Boolean, default=False, nullable=False, index=True)
    access_log = Column(JSONB, default=list, nullable=False)  # Audit log of viewers and export actions
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    report = relationship("SafetyReport", back_populates="evidence_package")
