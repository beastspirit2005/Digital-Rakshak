import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from infrastructure.db.session import Base
import enum


class TransactionType(str, enum.Enum):
    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"
    CARD = "CARD"
    NETBANKING = "NETBANKING"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    APPROVED_AND_MONITORED = "APPROVED_AND_MONITORED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    STEP_UP_VERIFIED = "STEP_UP_VERIFIED"
    HELD = "HELD"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class RiskBand(str, enum.Enum):
    LOW = "LOW"
    GUARDED = "GUARDED"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FrictionAction(str, enum.Enum):
    APPROVE = "APPROVE"
    APPROVE_AND_MONITOR = "APPROVE_AND_MONITOR"
    STEP_UP_VERIFICATION = "STEP_UP_VERIFICATION"
    TEMPORARY_HOLD = "TEMPORARY_HOLD"
    HOLD_AND_INVESTIGATE = "HOLD_AND_INVESTIGATE"


class FeedbackDecision(str, enum.Enum):
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    LEGITIMATE_ANOMALY = "LEGITIMATE_ANOMALY"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)
    beneficiary_id = Column(String, index=True, nullable=False)
    device_id = Column(String, index=True, nullable=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    transaction_type = Column(String, default=TransactionType.UPI.value, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    
    channel = Column(String, default="MOBILE", nullable=False)
    status = Column(String, default=TransactionStatus.PENDING.value, nullable=False, index=True)
    
    raw_metadata = Column(JSONB, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    features = relationship("TransactionFeature", back_populates="transaction", cascade="all, delete-orphan")
    score = relationship("TransactionScore", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    decision = relationship("TransactionDecision", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    feedbacks = relationship("TransactionFeedback", back_populates="transaction", cascade="all, delete-orphan")


class TransactionFeature(Base):
    __tablename__ = "transaction_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String, nullable=False, index=True)
    feature_value = Column(Float, nullable=False)
    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="features")


class TransactionScore(Base):
    __tablename__ = "transaction_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    risk_score = Column(Float, nullable=False, index=True)        # 0.0 to 1.0
    confidence = Column(Float, nullable=False)                    # 0.0 to 1.0
    risk_band = Column(String, nullable=False, index=True)        # LOW, GUARDED, ELEVATED, HIGH, CRITICAL
    sub_scores = Column(JSONB, default=dict, nullable=False)      # breakdown per signal
    model_version = Column(String, default="v1.0", nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="score")


class TransactionDecision(Base):
    __tablename__ = "transaction_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    decision = Column(String, nullable=False, index=True)         # APPROVE, STEP_UP_VERIFICATION, TEMPORARY_HOLD, etc.
    policy_version = Column(String, default="v1.0", nullable=False)
    reason_codes = Column(JSONB, default=list, nullable=False)    # ["NEW_DEVICE", "VELOCITY_SPIKE"]
    explanation_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="decision")


class DeviceProfile(Base):
    __tablename__ = "device_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    
    first_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    total_transactions = Column(Integer, default=1)
    associated_accounts = Column(JSONB, default=list)            # ["ACC-1", "ACC-2"]
    
    risk_score = Column(Float, default=0.0)
    is_emulator = Column(Boolean, default=False)
    ip_addresses = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BeneficiaryProfile(Base):
    __tablename__ = "beneficiary_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    beneficiary_id = Column(String, unique=True, index=True, nullable=False) # VPA or Account ID
    account_number = Column(String, nullable=True, index=True)
    ifsc_or_vpa = Column(String, nullable=True)
    
    first_received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    total_received_amount = Column(Float, default=0.0)
    total_transactions = Column(Integer, default=1)
    
    is_flagged = Column(Boolean, default=False, index=True)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TransactionFeedback(Base):
    __tablename__ = "transaction_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    investigator_id = Column(String, nullable=True)
    
    ai_risk_score = Column(Float, nullable=False)
    ai_decision = Column(String, nullable=False)
    human_decision = Column(String, nullable=False) # CONFIRMED_FRAUD, FALSE_POSITIVE, LEGITIMATE_ANOMALY
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="feedbacks")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    rule_name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    condition_expression = Column(String, nullable=False)
    action = Column(String, nullable=False)
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

