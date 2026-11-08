import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from infrastructure.db.session import Base


class BankIntegrationType(str, enum.Enum):
    SANDBOX_API = "SANDBOX_API"
    DIRECT_API = "DIRECT_API"
    NODAL_EMAIL = "NODAL_EMAIL"


class EscalationRole(str, enum.Enum):
    VICTIM_BANK = "VICTIM_BANK"
    BENEFICIARY_BANK = "BENEFICIARY_BANK"


class ApprovalTier(str, enum.Enum):
    AUTOMATED = "AUTOMATED"
    INVESTIGATOR_APPROVED = "INVESTIGATOR_APPROVED"
    SENIOR_OFFICER = "SENIOR_OFFICER"


class EscalationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    UNDER_REVIEW = "UNDER_REVIEW"
    INFORMATION_REQUIRED = "INFORMATION_REQUIRED"
    ACTION_REPORTED = "ACTION_REPORTED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class TransactionVerificationStatus(str, enum.Enum):
    EXTRACTED_UNVERIFIED = "EXTRACTED_UNVERIFIED"
    RESOLVED_INFERRED = "RESOLVED_INFERRED"
    VERIFIED = "VERIFIED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class BankResponseActionType(str, enum.Enum):
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    INFO_REQUEST = "INFO_REQUEST"
    ACTION_TAKEN = "ACTION_TAKEN"
    REJECTION = "REJECTION"


class BankRegistry(Base):
    """
    Authoritative Directory of Verified Indian Financial Institutions.
    Maps RBI/NPCI Bank Codes, IFSC Prefixes, and supported payment rails.
    """
    __tablename__ = "bank_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    bank_code = Column(String(32), unique=True, index=True, nullable=False)  # e.g. "SBIN", "HDFC"
    bank_name = Column(String(255), nullable=False)                         # e.g. "State Bank of India"
    rbi_code = Column(String(32), nullable=True)
    ifsc_prefix = Column(String(10), index=True, nullable=False)           # 4-char bank identifier
    supported_rails = Column(JSONB, default=lambda: ["UPI", "IMPS", "NEFT", "RTGS"], nullable=False)
    escalation_channels = Column(JSONB, default=lambda: {"api": True, "nodal_email": True}, nullable=False)
    integration_type = Column(String(32), default=BankIntegrationType.SANDBOX_API.value, nullable=False)
    api_endpoint = Column(String(500), nullable=True)
    nodal_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    escalations = relationship("BankEscalation", back_populates="target_bank")
    remitted_transactions = relationship("FinancialTransaction", foreign_keys="FinancialTransaction.remitter_bank_id", back_populates="remitter_bank")
    beneficiary_transactions = relationship("FinancialTransaction", foreign_keys="FinancialTransaction.beneficiary_bank_id", back_populates="beneficiary_bank")


class FinancialTransaction(Base):
    """
    Structured Financial Fraud Transaction linked to an official Case.
    Captures extracted or confirmed UTR/RRN, payment rail, remitter, and beneficiary metadata.
    """
    __tablename__ = "financial_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_reference = Column(String(64), index=True, nullable=True)  # UTR / RRN (e.g. 12 digits)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_rail = Column(String(32), default="UPI", nullable=False)       # UPI, IMPS, NEFT, RTGS, CARD
    transaction_time = Column(DateTime(timezone=True), nullable=True)

    # Remitter / Victim institution & account details
    remitter_bank_id = Column(UUID(as_uuid=True), ForeignKey("bank_registry.id", ondelete="SET NULL"), nullable=True, index=True)
    remitter_account_masked = Column(String(64), nullable=True)
    remitter_vpa = Column(String(255), nullable=True)

    # Beneficiary / Fraudster institution & account details
    beneficiary_bank_id = Column(UUID(as_uuid=True), ForeignKey("bank_registry.id", ondelete="SET NULL"), nullable=True, index=True)
    beneficiary_account_masked = Column(String(64), nullable=True)
    beneficiary_vpa = Column(String(255), nullable=True)

    verification_status = Column(String(32), default=TransactionVerificationStatus.EXTRACTED_UNVERIFIED.value, nullable=False, index=True)
    raw_extraction = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="financial_transactions")
    remitter_bank = relationship("BankRegistry", foreign_keys=[remitter_bank_id], back_populates="remitted_transactions")
    beneficiary_bank = relationship("BankRegistry", foreign_keys=[beneficiary_bank_id], back_populates="beneficiary_transactions")
    escalations = relationship("BankEscalation", back_populates="transaction", cascade="all, delete-orphan")


class BankEscalation(Base):
    """
    Bank-Specific Fraud Alert Entity.
    Tracks alert generation, approval status, payload signatures, and target bank routing.
    """
    __tablename__ = "bank_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("financial_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    alert_reference = Column(String(64), unique=True, index=True, nullable=False)  # e.g. "DR-ALERT-2026-0001"
    target_bank_id = Column(UUID(as_uuid=True), ForeignKey("bank_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_role = Column(String(32), nullable=False)                           # VICTIM_BANK | BENEFICIARY_BANK
    approval_tier = Column(String(32), default=ApprovalTier.INVESTIGATOR_APPROVED.value, nullable=False)
    status = Column(String(32), default=EscalationStatus.DRAFT.value, nullable=False, index=True)
    priority = Column(String(16), default="MEDIUM", nullable=False)

    alert_payload = Column(JSONB, nullable=False)                                  # Standardized JSON alert payload
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="bank_escalations")
    transaction = relationship("FinancialTransaction", back_populates="escalations")
    target_bank = relationship("BankRegistry", back_populates="escalations")
    approver = relationship("User", foreign_keys=[approved_by])
    delivery_attempts = relationship("BankDeliveryAttempt", back_populates="escalation", cascade="all, delete-orphan")
    responses = relationship("BankResponse", back_populates="escalation", cascade="all, delete-orphan")


class BankDeliveryAttempt(Base):
    """
    Log of API/Webhook transmission attempts with timestamps, HTTP statuses, and error tracking.
    """
    __tablename__ = "bank_delivery_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    escalation_id = Column(UUID(as_uuid=True), ForeignKey("bank_escalations.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    channel = Column(String(32), default="API", nullable=False)
    http_status_code = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    delivery_status = Column(String(32), nullable=False)                           # SUCCESS, FAILED, TIMED_OUT
    error_message = Column(Text, nullable=True)
    attempted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    escalation = relationship("BankEscalation", back_populates="delivery_attempts")


class BankResponse(Base):
    """
    Institutional Acknowledgement & Action Report received from a Bank.
    """
    __tablename__ = "bank_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    escalation_id = Column(UUID(as_uuid=True), ForeignKey("bank_escalations.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_reference_number = Column(String(128), nullable=True, index=True)
    response_type = Column(String(64), nullable=False)                             # ACKNOWLEDGEMENT, INFO_REQUEST, ACTION_TAKEN, REJECTION
    status_summary = Column(String(128), nullable=False)
    details = Column(JSONB, default=dict, nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    escalation = relationship("BankEscalation", back_populates="responses")
