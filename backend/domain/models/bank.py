import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey, Index, Numeric
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
    DEAD_LETTER = "DEAD_LETTER"
    RECONCILED = "RECONCILED"


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


class BankInstructionCategory(str, enum.Enum):
    """
    Distinguishes operational notices, statutory records requests,
    precautionary holds, and formal judicial/police seizure orders.
    """
    INFORMATIONAL_ALERT = "INFORMATIONAL_ALERT"        # Rapid fraud warning to stop outward layering
    RECORD_REQUEST_BNSS_94 = "RECORD_REQUEST_BNSS_94"  # Section 94 BNSS 2023 summons for KYC/records
    PROTECTIVE_HOLD_REQUEST = "PROTECTIVE_HOLD_REQUEST"# Precautionary temporary debit lien / escrow hold
    STATUTORY_FREEZE_ORDER = "STATUTORY_FREEZE_ORDER"  # Formal account seizure under Section 106/107 BNSS 2023


class ResolutionConfidenceType(str, enum.Enum):
    """
    Distinguishes candidate PSP routing arrangements (e.g. from VPA suffix)
    from confirmed account-holding banks (e.g. from IFSC or verified transaction metadata).
    """
    CONFIRMED_ACCOUNT_BANK = "CONFIRMED_ACCOUNT_BANK"
    CANDIDATE_PSP_ROUTING = "CANDIDATE_PSP_ROUTING"


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
    Enforces exact Decimal financial accounting and 5-tier balance reconciliation.
    """
    __tablename__ = "financial_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_reference = Column(String(64), index=True, nullable=True)  # UTR / RRN (e.g. 12 digits)
    
    # Financial precision and multi-tier reconciliation
    amount = Column(Numeric(14, 2), nullable=False)                        # Identified transfer amount
    reported_loss_amount = Column(Numeric(14, 2), nullable=True)           # Stated citizen loss
    amount_under_lien = Column(Numeric(14, 2), default=0.00, nullable=False) # Held in protective lien
    amount_frozen = Column(Numeric(14, 2), default=0.00, nullable=False)     # Formally seized under Sec 106 BNSS
    amount_recovered = Column(Numeric(14, 2), default=0.00, nullable=False)  # Repatriated to victim

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
    beneficiary_bank_confidence = Column(String(32), default=ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value, nullable=False)

    verification_status = Column(String(32), default=TransactionVerificationStatus.EXTRACTED_UNVERIFIED.value, nullable=False, index=True)
    raw_extraction = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="financial_transactions")
    remitter_bank = relationship("BankRegistry", foreign_keys=[remitter_bank_id], back_populates="remitted_transactions")
    beneficiary_bank = relationship("BankRegistry", foreign_keys=[beneficiary_bank_id], back_populates="beneficiary_transactions")
    escalations = relationship("BankEscalation", back_populates="transaction", cascade="all, delete-orphan")
    fund_positions = relationship("FinancialFundPosition", back_populates="transaction", cascade="all, delete-orphan")


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
    
    instruction_category = Column(String(32), default=BankInstructionCategory.INFORMATIONAL_ALERT.value, nullable=False)
    statutory_basis = Column(String(64), default="RBI_CUSTOMER_PROTECTION_2017", nullable=False)
    beneficiary_bank_confidence = Column(String(32), default=ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value, nullable=False)

    approval_tier = Column(String(32), default=ApprovalTier.INVESTIGATOR_APPROVED.value, nullable=False)
    status = Column(String(32), default=EscalationStatus.DRAFT.value, nullable=False, index=True)
    priority = Column(String(16), default="MEDIUM", nullable=False)

    alert_payload = Column(JSONB, nullable=False)                                  # Standardized JSON alert payload
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
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
    Each physical attempt retains a distinct attempt_id while honoring the logical parent's idempotency key.
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
    Tracks frozen and actioned balances with exact Decimal financial precision.
    """
    __tablename__ = "bank_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    escalation_id = Column(UUID(as_uuid=True), ForeignKey("bank_escalations.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_reference_number = Column(String(128), nullable=True, index=True)
    response_type = Column(String(64), nullable=False)                             # ACKNOWLEDGEMENT, INFO_REQUEST, ACTION_TAKEN, REJECTION
    status_summary = Column(String(128), nullable=False)
    funds_frozen_amount = Column(Numeric(14, 2), nullable=True)
    funds_actioned_amount = Column(Numeric(14, 2), nullable=True)
    details = Column(JSONB, default=dict, nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    escalation = relationship("BankEscalation", back_populates="responses")


class FraudResponseStage(str, enum.Enum):
    """
    Formal 8-stage state machine governing every fraud incident
    from citizen report to multi-bank financial reconciliation.
    """
    FRAUD_REPORTED = "FRAUD_REPORTED"
    TRANSACTION_IDENTIFIED = "TRANSACTION_IDENTIFIED"
    BANKS_RESOLVED = "BANKS_RESOLVED"
    ESCALATION_CREATED = "ESCALATION_CREATED"
    APPROVAL_EVALUATED = "APPROVAL_EVALUATED"
    NOTICE_DISPATCHED = "NOTICE_DISPATCHED"
    BANK_RESPONSE_RECEIVED = "BANK_RESPONSE_RECEIVED"
    FINANCIAL_STATUS_RECONCILED = "FINANCIAL_STATUS_RECONCILED"


class FraudResponseLifecycleEvent(Base):
    """
    Immutable, append-only event ledger tracking the end-to-end lifecycle
    of a fraud response from citizen report to bank reconciliation.
    Maintains a cryptographic SHA-256 Merkle hash chain for Section 63 BSA 2023 admissibility.
    """
    __tablename__ = "fraud_response_lifecycle_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    correlation_id = Column(String(128), index=True, nullable=False) # Global trace ID connecting all actions
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("financial_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    escalation_id = Column(UUID(as_uuid=True), ForeignKey("bank_escalations.id", ondelete="SET NULL"), nullable=True, index=True)

    stage = Column(String(64), nullable=False, index=True)
    previous_stage = Column(String(64), nullable=True)
    actor_or_service = Column(String(128), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    transition_reason = Column(Text, nullable=False)
    evidence_reference = Column(String(128), nullable=True)
    
    financial_snapshot = Column(JSONB, nullable=True)
    metadata_payload = Column(JSONB, default=dict, nullable=False)

    event_hash = Column(String(64), nullable=False, index=True) # SHA-256 hash of this event + previous_event_hash
    previous_event_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class WebhookNonceReplayCache(Base):
    """
    Persistent replay-prevention cache tracking bank callback signatures and nonces.
    Prevents replay attacks and duplicate webhook processing within 24-hour window.
    """
    __tablename__ = "webhook_nonce_replay_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    bank_code = Column(String(32), index=True, nullable=False)
    nonce = Column(String(128), unique=True, index=True, nullable=False)
    signature = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), index=True, nullable=False)


class InvestigatorDecisionAudit(Base):
    """
    Audit trail recording human clearances: who approved, evidence reviewed,
    statutory powers invoked under BNSS 2023, and digital authorization tokens.
    """
    __tablename__ = "investigator_decision_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    escalation_id = Column(UUID(as_uuid=True), ForeignKey("bank_escalations.id", ondelete="CASCADE"), nullable=False, index=True)
    investigator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(32), nullable=False) # APPROVED, REJECTED, MODIFIED
    reviewed_evidence_ids = Column(JSONB, default=list, nullable=False)
    statutory_powers_invoked = Column(String(64), nullable=False) # SECTION_94_BNSS, SECTION_106_BNSS
    decision_rationale = Column(Text, nullable=False)
    authorization_token = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class InstitutionalOutboxEvent(Base):
    """
    Transactional Outbox for reliable, crash-safe institutional delivery.
    Guarantees at-least-once dispatch without dual-write hazards.
    """
    __tablename__ = "institutional_outbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=False, index=True)
    payload = Column(JSONB, default=dict, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True) # PENDING, PROCESSING, COMPLETED, FAILED, DEAD_LETTER
    attempt_count = Column(Integer, default=0, nullable=False)
    available_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(128), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_error_code = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class OutboxWorkerRun(Base):
    """
    Audit log of outbox worker invocations, heartbeats, and throughput metrics.
    Enables operational visibility into Vercel crons and background execution.
    """
    __tablename__ = "outbox_worker_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    trigger_type = Column(String(32), default="CRON", nullable=False) # CRON, ON_DEMAND, DAEMON, MANUAL
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    events_claimed = Column(Integer, default=0, nullable=False)
    events_processed = Column(Integer, default=0, nullable=False)
    events_retry_scheduled = Column(Integer, default=0, nullable=False)
    events_dead_lettered = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="RUNNING", nullable=False, index=True) # RUNNING, SUCCESS, PARTIAL_FAILURE, TIMEOUT_ABORTED, FAILED
    error_summary = Column(Text, nullable=True)


class FinancialFundPosition(Base):
    """
    Account-level or transaction-leg fund position ledger.
    Resolves the secured-funds overlap problem by tracking distinct unique fund positions.
    0 <= recovered_amount <= max(lien_amount, frozen_amount) <= original_amount
    """
    __tablename__ = "financial_fund_positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("financial_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    account_reference_masked = Column(String(64), nullable=False)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("bank_registry.id", ondelete="SET NULL"), nullable=True, index=True)
    original_amount = Column(Numeric(14, 2), nullable=False)
    lien_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    frozen_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    recovered_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)
    source_reference = Column(String(128), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    transaction = relationship("FinancialTransaction", back_populates="fund_positions")
    bank = relationship("BankRegistry")


class EvidenceCheckpoint(Base):
    """
    Cryptographic checkpoint anchoring a sequential range of lifecycle events with an external digital signature.
    """
    __tablename__ = "evidence_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_start = Column(Integer, nullable=False)
    sequence_end = Column(Integer, nullable=False)
    merkle_root_hash = Column(String(64), nullable=False, index=True)
    signature = Column(String(256), nullable=False)
    signing_key_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("Case")


class EvidenceAccessEvent(Base):
    """
    Immutable access log tracking chain of custody for evidentiary records without storing confidential contents.
    """
    __tablename__ = "evidence_access_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_role = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False, index=True) # UPLOADED, VIEWED, DOWNLOADED, EXPORTED, SHARED, ACCESS_DENIED, INTEGRITY_VERIFIED
    evidence_reference = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("Case")
    actor = relationship("User")
