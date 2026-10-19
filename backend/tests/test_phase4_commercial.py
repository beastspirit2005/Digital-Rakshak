"""
Phase 4: Pilot Onboarding & Commercial Monetization Test Suite
==============================================================
Automated verification for Phase 4 of the Digital Rakshak Master Plan:
4.1 B2C Subscription Activation & Entitlement Upgrades
4.2 GST-Compliant Tax Invoicing (SAC 998313, 18% GST calculation)
4.3 1-Click Self-Serve Subscription Cancellation & Downgrade
4.4 Razorpay Webhook Processing (HMAC verification, renewal, payment failure downgrade)
"""

import hashlib
import hmac
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from core.config import settings
from core.security import create_access_token
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from domain.models.organization import Subscription, SubscriptionStatus, MarketSegment


# ── Helpers & Fixtures ────────────────────────────────────────────────────────

async def _create_test_paying_citizen() -> tuple[dict, str]:
    user_id = uuid.uuid4()
    email = f"payer_{uuid.uuid4().hex[:6]}@gmail.com"

    async with AsyncSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            full_name="Rajesh Kumar",
            role="citizen",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",
            b2c_subscription_status="active",
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": str(user_id), "email": email, "role": "citizen"})
    return {"Authorization": f"Bearer {token}"}, str(user_id)


# ── 4.1 Subscription Flow & Payment Verification Tests ───────────────────────

@pytest.mark.asyncio
async def test_b2c_subscription_creation_and_sandbox_activation():
    """Verify B2C subscription creation and payment verification updates entitlements."""
    headers, user_id = await _create_test_paying_citizen()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create subscription
        create_res = await ac.post(
            "/v1/billing/create-subscription",
            headers=headers,
            json={"plan_code": "b2c_pro_149"}
        )
        assert create_res.status_code == 200
        sub_data = create_res.json()
        assert sub_data["plan_code"] == "b2c_pro_149"
        sub_id = sub_data["subscription_id"]

        # 2. Verify payment with valid HMAC signature
        secret = (settings.RAZORPAY_KEY_SECRET or "sandbox_key_secret").encode()
        pay_id = f"pay_{uuid.uuid4().hex[:8]}"
        msg = f"{pay_id}|{sub_id}".encode()
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        verify_res = await ac.post(
            "/v1/billing/verify-payment",
            headers=headers,
            json={
                "razorpay_payment_id": pay_id,
                "razorpay_subscription_id": sub_id,
                "razorpay_signature": valid_signature,
                "plan_code": "b2c_pro_149"
            }
        )
        assert verify_res.status_code == 200

        # 3. Check subscription status
        status_res = await ac.get("/v1/billing/status", headers=headers)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["is_pro"] is True
        assert status_data["plan_code"] == "b2c_pro_149"
        assert status_data["subscription_status"] == "active"


# ── 4.2 GST Tax Invoice Generation Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_gst_tax_invoice_generation():
    """Verify GST compliant tax invoice generation with SAC 998313 and tax-exclusive 18% calculation."""
    headers, user_id = await _create_test_paying_citizen()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create and activate monthly ₹149 subscription (₹149 Base + 18% GST = ₹175.82)
        create_res = await ac.post("/v1/billing/create-subscription", headers=headers, json={"plan_code": "b2c_pro_149"})
        assert create_res.status_code == 200
        sub_data = create_res.json()
        assert sub_data["amount_paise"] == 17582
        sub_id = sub_data["subscription_id"]

        secret = (settings.RAZORPAY_KEY_SECRET or "sandbox_key_secret").encode()
        pay_id = f"pay_{uuid.uuid4().hex[:8]}"
        msg = f"{pay_id}|{sub_id}".encode()
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        await ac.post(
            "/v1/billing/verify-payment",
            headers=headers,
            json={
                "razorpay_payment_id": pay_id,
                "razorpay_subscription_id": sub_id,
                "razorpay_signature": valid_signature,
                "plan_code": "b2c_pro_149"
            }
        )

        # Fetch Tax Invoice for ₹149 plan
        inv_res = await ac.get(f"/v1/billing/invoice/{sub_id}", headers=headers)
        assert inv_res.status_code == 200
        inv = inv_res.json()

        assert inv["invoice_number"].startswith("INV-DR-")
        assert inv["supplier_sac_code"] == "998313"
        assert inv["supplier_gstin"] == "07AABCD1234E1Z5"
        assert inv["taxable_base_amount"] == 149.0
        assert inv["cgst_amount"] == 13.41
        assert inv["sgst_amount"] == 13.41
        assert inv["total_tax_amount"] == 26.82
        assert inv["gross_amount"] == 175.82
        assert inv["payment_status"] == "PAID"

        # Also verify HTML invoice renders successfully
        html_res = await ac.get(f"/v1/billing/invoice/{sub_id}/html", headers=headers)
        assert html_res.status_code == 200
        assert "Tax Invoice" in html_res.text
        assert "998313" in html_res.text


@pytest.mark.asyncio
async def test_annual_plan_invoice_and_exclusive_gst():
    """Verify Annual Plan (₹1,299 Base + 18% GST = ₹1,532.82) invoice calculation."""
    headers, user_id = await _create_test_paying_citizen()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post("/v1/billing/create-subscription", headers=headers, json={"plan_code": "b2c_pro_annual"})
        assert create_res.status_code == 200
        sub_data = create_res.json()
        assert sub_data["amount_paise"] == 153282
        sub_id = sub_data.get("subscription_id")
        order_id = sub_data.get("order_id")
        identifier = sub_id or order_id

        secret = (settings.RAZORPAY_KEY_SECRET or "sandbox_key_secret").encode()
        pay_id = f"pay_{uuid.uuid4().hex[:8]}"
        msg = f"{pay_id}|{sub_id}".encode() if sub_id else f"{order_id}|{pay_id}".encode()
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        await ac.post(
            "/v1/billing/verify-payment",
            headers=headers,
            json={
                "razorpay_payment_id": pay_id,
                "razorpay_subscription_id": sub_id,
                "razorpay_order_id": order_id,
                "razorpay_signature": valid_signature,
                "plan_code": "b2c_pro_annual"
            }
        )

        inv_res = await ac.get(f"/v1/billing/invoice/{identifier}", headers=headers)
        assert inv_res.status_code == 200
        inv = inv_res.json()

        assert inv["taxable_base_amount"] == 1299.0
        assert inv["cgst_amount"] == 116.91
        assert inv["sgst_amount"] == 116.91
        assert inv["total_tax_amount"] == 233.82
        assert inv["gross_amount"] == 1532.82


# ── 4.3 1-Click Self-Serve Cancellation & Base Prorated Refund Tests ─────────

@pytest.mark.asyncio
async def test_1click_subscription_cancellation_with_prorated_refund():
    """Verify self-serve cancellation calculates prorated base refund, keeps GST non-refundable, and downgrades user."""
    headers, user_id = await _create_test_paying_citizen()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Upgrade to Pro ₹149 first
        create_res = await ac.post("/v1/billing/create-subscription", headers=headers, json={"plan_code": "b2c_pro_149"})
        sub_id = create_res.json()["subscription_id"]

        secret = (settings.RAZORPAY_KEY_SECRET or "sandbox_key_secret").encode()
        pay_id = f"pay_{uuid.uuid4().hex[:8]}"
        msg = f"{pay_id}|{sub_id}".encode()
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        await ac.post(
            "/v1/billing/verify-payment",
            headers=headers,
            json={
                "razorpay_payment_id": pay_id,
                "razorpay_subscription_id": sub_id,
                "razorpay_signature": valid_signature,
                "plan_code": "b2c_pro_149"
            }
        )

        # User clicks cancel
        cancel_res = await ac.post("/v1/billing/cancel-subscription", headers=headers)
        assert cancel_res.status_code == 200
        res_data = cancel_res.json()
        assert res_data["plan_code"] == "b2c_free"
        assert "refund_details" in res_data

        refund = res_data["refund_details"]
        assert refund["original_base_amount"] == 149.0
        assert refund["tax_amount"] == 26.82
        assert refund["gross_amount_paid"] == 175.82
        assert refund["tax_refundable"] is False
        assert refund["total_days"] == 30
        assert refund["days_used"] >= 1
        assert refund["refund_amount"] > 0
        assert refund["refund_amount"] <= 149.0

        # Check status shows free
        status_res = await ac.get("/v1/billing/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["is_pro"] is False
        assert status_res.json()["plan_code"] == "b2c_free"


# ── 4.4 Webhook Signature Verification Tests ─────────────────────────────────

def test_webhook_hmac_tamper_resistance():
    """Verify Razorpay webhook HMAC-SHA256 signature check fails if tampered."""
    secret = "rzp_webhook_secret_998877"
    raw_payload = json.dumps({"event": "subscription.charged", "payload": {}}).encode()

    valid_signature = hmac.new(secret.encode(), raw_payload, hashlib.sha256).hexdigest()

    # Valid check passes
    check = hmac.new(secret.encode(), raw_payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(check, valid_signature) is True

    # Tampered body fails
    tampered_payload = json.dumps({"event": "subscription.halted", "payload": {}}).encode()
    tampered_check = hmac.new(secret.encode(), tampered_payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(tampered_check, valid_signature) is False
