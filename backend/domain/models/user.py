import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer
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
    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_failed_attempts = Column(Integer, default=0, server_default="0")
    otp_lockout_count = Column(Integer, default=0, server_default="0")
    otp_locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
