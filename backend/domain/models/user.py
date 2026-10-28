import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    station_phone_number = Column(String, nullable=True) # Used by police role to allow victims to contact them
    role = Column(String, default="citizen", nullable=False) # Roles: citizen, bank_employee, police, cyber_cell, admin
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False) # True by default for citizens, False for others requiring admin approval
    is_verified = Column(Boolean, default=False, nullable=False, server_default="false") # Email OTP verification state

    # Duty Location & Station Information
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    station_name = Column(String(255), nullable=True)
    badge_number = Column(String(50), nullable=True)
    designation = Column(String(120), nullable=True)

    # Official KYC Documents & Review Metadata
    kyc_org_id_path = Column(String(500), nullable=True)
    kyc_org_id_filename = Column(String(255), nullable=True)
    kyc_aadhaar_path = Column(String(500), nullable=True)
    kyc_aadhaar_filename = Column(String(255), nullable=True)
    kyc_submitted_at = Column(DateTime(timezone=True), nullable=True)
    kyc_reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    kyc_review_notes = Column(Text, nullable=True)

    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_failed_attempts = Column(Integer, default=0, server_default="0")
    otp_lockout_count = Column(Integer, default=0, server_default="0")
    otp_locked_until = Column(DateTime(timezone=True), nullable=True)
    # B2C subscription state — cached here for fast entitlement checks
    b2c_plan_code = Column(String, default="b2c_free", nullable=False, server_default="b2c_free")
    b2c_subscription_status = Column(String, default="active", nullable=False, server_default="active")
    # Razorpay customer ID — set on first checkout
    razorpay_customer_id = Column(String, nullable=True)
    # Chat Safety Transparency acceptance
    chat_safety_policy_version = Column(String(20), nullable=True)
    chat_safety_accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
