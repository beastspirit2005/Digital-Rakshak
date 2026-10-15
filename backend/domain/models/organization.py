"""
Multi-Tenant Domain Models
===========================
Introduces Organizations, API Keys, Subscriptions, and Usage Quotas to
support the Digital Rakshak Business (B2B) tier alongside the existing
B2C consumer tier.

Design decisions
----------------
* All PKs are UUID v4 to avoid enumeration attacks.
* API keys are stored as SHA-256 hashes — the plaintext is shown once at
  creation time and never persisted (similar to GitHub PAT model).
* Subscriptions table unifies B2C (user-linked) and B2B (org-linked) plans.
* UsageQuota tracks per-period event ingestion against monthly limits.
"""

from __future__ import annotations

import enum
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from infrastructure.db.session import Base


# ── Enumerations ─────────────────────────────────────────────────────────────

class OrgTier(str, enum.Enum):
    STARTER    = "starter"
    BUSINESS   = "business"
    ENTERPRISE = "enterprise"


class OrgMemberRole(str, enum.Enum):
    OWNER   = "owner"
    ADMIN   = "admin"
    ANALYST = "analyst"
    VIEWER  = "viewer"


class MarketSegment(str, enum.Enum):
    B2C = "b2c"
    B2B = "b2b"


class PlanCode(str, enum.Enum):
    # B2C
    B2C_FREE = "b2c_free"
    B2C_PRO_149 = "b2c_pro_149"   # ₹149/month
    B2C_PRO_249 = "b2c_pro_249"   # ₹249/month
    B2C_PRO_ANNUAL = "b2c_pro_annual"  # ₹1299/year
    # B2B
    B2B_PILOT    = "b2b_pilot"     # ₹9,999 one-time 30-day sandbox
    B2B_STARTER  = "b2b_starter"   # ₹9,999/month
    B2B_BUSINESS = "b2b_business"  # ₹19,999/month
    B2B_ENTERPRISE = "b2b_enterprise"  # Custom


class SubscriptionStatus(str, enum.Enum):
    ACTIVE    = "active"
    TRIALING  = "trialing"
    PAST_DUE  = "past_due"
    HALTED    = "halted"       # Razorpay subscription.halted
    CANCELED  = "canceled"
    EXPIRED   = "expired"


# ── Organization ─────────────────────────────────────────────────────────────

class Organization(Base):
    """
    Represents a company / institution using the B2B enterprise tier.
    All B2B cases, events, and API keys are scoped to an organization.
    """
    __tablename__ = "organizations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name       = Column(String(255), nullable=False)
    slug       = Column(String(100), unique=True, index=True, nullable=False)
    tier       = Column(String(50), default=OrgTier.STARTER.value, nullable=False)
    domain     = Column(String(255), nullable=True)   # e.g. acme.com — for SSO hints
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    members      = relationship("OrganizationMember", back_populates="organization",
                                cascade="all, delete-orphan")
    api_keys     = relationship("ApiKey", back_populates="organization",
                                cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization")
    usage_quotas = relationship("UsageQuota", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug} tier={self.tier}>"


# ── Organization Member ───────────────────────────────────────────────────────

class OrganizationMember(Base):
    """
    Maps a User to an Organization with a specific role.
    A user can belong to multiple organizations.
    """
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_user"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role       = Column(String(50), default=OrgMemberRole.ANALYST.value, nullable=False)
    is_active  = Column(Boolean, default=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    joined_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="members")

    def __repr__(self) -> str:
        return f"<OrganizationMember org={self.org_id} user={self.user_id} role={self.role}>"


# ── API Key ───────────────────────────────────────────────────────────────────

class ApiKey(Base):
    """
    SHA-256 hashed API key for B2B machine-to-machine authentication.

    The plaintext key (``dr_live_<random>``) is returned once at creation
    and never stored.  Only the SHA-256 hash is persisted.
    """
    __tablename__ = "api_keys"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    name        = Column(String(100), nullable=False)          # human label
    key_prefix  = Column(String(12), nullable=False, index=True)  # first 12 chars for lookup
    key_hash    = Column(String(64), nullable=False, unique=True)  # SHA-256 hex digest
    scopes      = Column(JSONB, nullable=False, default=list)   # e.g. ["events:write", "alerts:read"]
    is_active   = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at  = Column(DateTime(timezone=True), nullable=True)  # None = never expires
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key triple: ``(plaintext, prefix, sha256_hash)``.

        Usage::

            plaintext, prefix, key_hash = ApiKey.generate_key()
            # Store prefix + key_hash; return plaintext to the user once.
        """
        raw = f"dr_live_{secrets.token_urlsafe(32)}"
        prefix = raw[:12]
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, digest

    @staticmethod
    def hash_key(plaintext: str) -> str:
        """Hash an incoming ``x-api-key`` header value for DB lookup."""
        return hashlib.sha256(plaintext.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"<ApiKey org={self.org_id} prefix={self.key_prefix} active={self.is_active}>"


# ── Subscription ──────────────────────────────────────────────────────────────

class Subscription(Base):
    """
    Unified subscription record for both B2C (user-linked) and B2B (org-linked) plans.

    Razorpay fields
    ---------------
    * ``razorpay_customer_id`` — Razorpay Customer object ID (``cust_xxx``).
    * ``razorpay_subscription_id`` — Razorpay Subscription ID (``sub_xxx``).
    * ``razorpay_plan_id`` — Razorpay Plan ID (``plan_xxx``).

    For B2C: ``user_id`` is set, ``org_id`` is NULL.
    For B2B: ``org_id`` is set, ``user_id`` is the billing contact.
    """
    __tablename__ = "subscriptions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # B2C link
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    # B2B link
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)

    market      = Column(String(10), nullable=False)           # "b2c" | "b2b"
    plan_code   = Column(String(50), nullable=False)           # PlanCode enum value
    status      = Column(String(30), default=SubscriptionStatus.TRIALING.value, nullable=False)

    # Razorpay references
    razorpay_customer_id      = Column(String(100), nullable=True)
    razorpay_subscription_id  = Column(String(100), nullable=True, index=True)
    razorpay_plan_id          = Column(String(100), nullable=True)
    razorpay_order_id         = Column(String(100), nullable=True)  # for one-off orders (B2B pilot)

    # Billing period
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end   = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    cancel_at_period_end = Column(Boolean, default=False)
    plan_metadata = Column("metadata", JSONB, nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")

    def __repr__(self) -> str:
        return (
            f"<Subscription plan={self.plan_code} status={self.status} "
            f"user={self.user_id} org={self.org_id}>"
        )


# ── Usage Quota ───────────────────────────────────────────────────────────────

class UsageQuota(Base):
    """
    Tracks monthly event ingestion usage per organization.
    One row per (org_id, period) pair, e.g., ("org-uuid", "2026-10").
    """
    __tablename__ = "usage_quotas"
    __table_args__ = (
        UniqueConstraint("org_id", "period", name="uq_org_period"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id           = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    period           = Column(String(7), nullable=False)   # "YYYY-MM"
    events_processed = Column(Integer, default=0, nullable=False)
    monthly_limit    = Column(Integer, default=50_000, nullable=False)  # default 50k/month
    overage_count    = Column(Integer, default=0, nullable=False)
    # Warning thresholds (percent): 80 → warning email, 100 → throttle
    last_warned_pct  = Column(Integer, nullable=True)
    updated_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="usage_quotas")

    @property
    def usage_pct(self) -> float:
        """Returns current usage as a percentage of the monthly limit."""
        if self.monthly_limit == 0:
            return 100.0
        return round((self.events_processed / self.monthly_limit) * 100.0, 2)


    @property
    def is_over_limit(self) -> bool:
        return self.events_processed >= self.monthly_limit

    def __repr__(self) -> str:
        return (
            f"<UsageQuota org={self.org_id} period={self.period} "
            f"{self.events_processed}/{self.monthly_limit}>"
        )
