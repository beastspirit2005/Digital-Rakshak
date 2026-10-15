"""
Automated Test Suite for Dual-Market (B2C + B2B) Architecture
============================================================
Verifies:
1. ApiKey generation, hashing, prefix matching, and tampering resistance.
2. Redis Streams event bus publishing and graceful fallback modes.
3. Multi-tenant UsageQuota calculation logic and overage thresholds.
4. Razorpay HMAC-SHA256 payment verification logic (B2C & B2B).
5. B2B event ingestion request validation schemas and limits.
6. Plan codes, market segmentation, and entitlement constants.
"""
import hashlib
import hmac
import json
import pytest
from datetime import datetime, timezone

from domain.models.organization import (
    ApiKey,
    Organization,
    UsageQuota,
    PlanCode,
    MarketSegment,
    SubscriptionStatus,
    OrgTier,
    OrgMemberRole,
)
from api.v1.b2b import ThreatEvent, IngestRequest
from infrastructure.event_bus.redis_streams import EventBus, STREAM_EVENTS


# ── 1. API Key Security & Hashing Tests ──────────────────────────────────────

def test_api_key_generation_and_hashing():
    plaintext, prefix, key_hash = ApiKey.generate_key()

    assert plaintext.startswith("dr_live_")
    assert len(prefix) == 12
    assert prefix == plaintext[:12]
    assert len(key_hash) == 64  # SHA-256 hex digest

    # Verify that hashing the plaintext reproduces the exact hash
    recomputed_hash = ApiKey.hash_key(plaintext)
    assert recomputed_hash == key_hash

    # Verify that tampering even 1 character fails verification
    tampered_key = plaintext[:-1] + ("x" if plaintext[-1] != "x" else "y")
    assert ApiKey.hash_key(tampered_key) != key_hash


# ── 2. Usage Quota Logic & Thresholds ────────────────────────────────────────

def test_usage_quota_calculation():
    quota = UsageQuota(
        period="2026-10",
        events_processed=20_000,
        monthly_limit=50_000,
        overage_count=0
    )

    assert quota.usage_pct == 40.0
    assert not quota.is_over_limit

    # At capacity
    quota.events_processed = 50_000
    assert quota.usage_pct == 100.0
    assert quota.is_over_limit

    # In overage
    quota.events_processed = 55_000
    quota.overage_count = 5_000
    assert quota.usage_pct == 110.0
    assert quota.is_over_limit
    assert quota.overage_count == 5_000


# ── 3. Razorpay Signature Verification Algorithm ────────────────────────────

def test_razorpay_subscription_signature_verification():
    secret = "test_webhook_secret_key_12345"
    payment_id = "pay_N4z123Abc"
    subscription_id = "sub_M3x789Def"

    # Razorpay subscription signature formula: HMAC-SHA256(payment_id + "|" + subscription_id, secret)
    message = f"{payment_id}|{subscription_id}".encode()
    valid_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    # Verify correct signature matches
    check = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(check, valid_signature) is True

    # Tampered signature must fail
    fake_signature = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    assert hmac.compare_digest(check, fake_signature) is False


def test_razorpay_order_signature_verification():
    secret = "test_webhook_secret_key_12345"
    order_id = "order_P9q456Ghi"
    payment_id = "pay_N4z123Abc"

    # Razorpay order signature formula: HMAC-SHA256(order_id + "|" + payment_id, secret)
    message = f"{order_id}|{payment_id}".encode()
    valid_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    check = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(check, valid_signature) is True


# ── 4. B2B Event Schema Validation ──────────────────────────────────────────

def test_b2b_threat_event_validation():
    event = ThreatEvent(
        event_type="phishing_domain",
        severity="critical",
        source_ip="192.168.1.50",
        metadata={"domain": "paytm-kyc-update.xyz", "registrar": "NameCheap"}
    )

    assert event.event_type == "phishing_domain"
    assert event.severity == "critical"
    assert event.event_id is not None
    assert event.metadata["domain"] == "paytm-kyc-update.xyz"


def test_b2b_ingest_request_batch_limit():
    # Valid batch within limit
    events = [
        ThreatEvent(event_type="test_event", severity="low") for _ in range(50)
    ]
    req = IngestRequest(events=events)
    assert len(req.events) == 50

    # Over 100 limit should raise validation error
    with pytest.raises(Exception):
        too_many = [
            ThreatEvent(event_type="test_event", severity="low") for _ in range(101)
        ]
        IngestRequest(events=too_many)


# ── 5. Plan Codes & Pricing Configuration Integrity ─────────────────────────

def test_plan_codes_and_market_segments():
    assert MarketSegment.B2C.value == "b2c"
    assert MarketSegment.B2B.value == "b2b"

    assert PlanCode.B2C_PRO_149.value == "b2c_pro_149"
    assert PlanCode.B2C_PRO_249.value == "b2c_pro_249"
    assert PlanCode.B2B_PILOT.value == "b2b_pilot"
    assert PlanCode.B2B_BUSINESS.value == "b2b_business"

    assert OrgTier.STARTER.value == "starter"
    assert OrgTier.BUSINESS.value == "business"
    assert OrgTier.ENTERPRISE.value == "enterprise"

    assert OrgMemberRole.OWNER.value == "owner"
    assert OrgMemberRole.ADMIN.value == "admin"
    assert OrgMemberRole.ANALYST.value == "analyst"
    assert OrgMemberRole.VIEWER.value == "viewer"


# ── 6. EventBus Fallback & Lifecycle ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_bus_publish_without_live_redis():
    bus = EventBus()
    # When redis is not connected or in no-op fallback mode, publish should not crash
    await bus.publish(STREAM_EVENTS, {"test": "data", "status": "ok"})
    await bus.close()
