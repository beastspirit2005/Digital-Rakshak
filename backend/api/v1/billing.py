"""
Razorpay Billing Router
========================
Handles B2C subscription creation, B2B order generation, payment
verification, webhook processing, and subscription status queries.

Flow diagrams
-------------

B2C Pro Subscription (UPI AutoPay / Card)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. Frontend calls ``POST /v1/billing/create-subscription``
2. Backend creates Razorpay Customer + Subscription → returns ``subscription_id``
3. Frontend opens Razorpay Standard Checkout with subscription_id
4. User authenticates UPI mandate / card
5. Razorpay sends ``subscription.authenticated`` webhook → backend activates plan
6. Recurring charges happen monthly; ``subscription.charged`` confirms payment

B2B Pilot / Business Order (One-off or recurring)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. Frontend calls ``POST /v1/billing/create-order`` with plan_code
2. Backend creates Razorpay Order → returns ``order_id`` + ``amount``
3. Frontend opens Razorpay Standard Checkout
4. User pays
5. Frontend calls ``POST /v1/billing/verify-payment`` with signature
6. Backend verifies HMAC → activates subscription record

Webhook security
----------------
All webhook events are verified using HMAC-SHA256 over the raw request body
with ``RAZORPAY_WEBHOOK_SECRET``.  Only then is the database updated.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, OFFICIAL_INSTITUTIONAL_ROLES
from core.config import settings
from domain.models.organization import (
    PlanCode,
    Subscription,
    SubscriptionStatus,
    MarketSegment,
)
from domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions (Razorpay)"])


class _MockEntity:
    def __init__(self, prefix: str):
        self._prefix = prefix
    def create(self, data: dict):
        return {"id": f"{self._prefix}_{uuid.uuid4().hex[:14]}", **data}

class _SandboxRazorpayClient:
    def __init__(self):
        self.customer = _MockEntity("cust_sandbox")
        self.plan = _MockEntity("plan_sandbox")
        self.subscription = _MockEntity("sub_sandbox")
        self.order = _MockEntity("order_sandbox")

def _get_razorpay_client():
    """Lazily initialise Razorpay client, or Sandbox fallback in local dev."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.info("Razorpay keys not configured — running in Sandbox billing mode.")
        return _SandboxRazorpayClient()
    if settings.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder") or settings.RAZORPAY_KEY_ID == "rzp_test_sandbox":
        return _SandboxRazorpayClient()
    import razorpay
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )



# ── Plan metadata ─────────────────────────────────────────────────────────────

_B2C_PLANS: Dict[str, Dict[str, Any]] = {
    PlanCode.B2C_PRO_149.value: {
        "amount":   14900,   # paise (₹149)
        "currency": "INR",
        "period":   "monthly",
        "interval": 1,
        "name":     "Digital Rakshak Pro (₹149/month)",
    },
    PlanCode.B2C_PRO_249.value: {
        "amount":   24900,   # paise (₹249)
        "currency": "INR",
        "period":   "monthly",
        "interval": 1,
        "name":     "Digital Rakshak Pro Plus (₹249/month)",
    },
    PlanCode.B2C_PRO_ANNUAL.value: {
        "amount":   129900,  # paise (₹1299)
        "currency": "INR",
        "period":   "yearly",
        "interval": 1,
        "name":     "Digital Rakshak Pro Annual (₹1299/year)",
    },
}

_B2B_ORDERS: Dict[str, Dict[str, Any]] = {
    PlanCode.B2B_PILOT.value: {
        "amount":   999900,   # paise (₹9,999)
        "currency": "INR",
        "name":     "Digital Rakshak B2B Pilot (30 days)",
        "duration_days": 30,
    },
    PlanCode.B2B_STARTER.value: {
        "amount":   999900,   # paise (₹9,999/month)
        "currency": "INR",
        "name":     "Digital Rakshak Business Starter",
        "duration_days": 30,
    },
    PlanCode.B2B_BUSINESS.value: {
        "amount":   1999900,  # paise (₹19,999/month)
        "currency": "INR",
        "name":     "Digital Rakshak Business",
        "duration_days": 30,
    },
}


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    plan_code: str = Field(
        ...,
        description=f"One of: {', '.join(_B2C_PLANS.keys())}",
        examples=["b2c_pro_149"],
    )


class CreateSubscriptionResponse(BaseModel):
    subscription_id:    Optional[str] = None
    order_id:           Optional[str] = None
    razorpay_key_id:    str
    plan_code:          str
    amount_paise:       int
    currency:           str


class CreateOrderRequest(BaseModel):
    plan_code: str = Field(
        ...,
        description=f"One of: {', '.join(_B2B_ORDERS.keys())}",
    )
    org_id: Optional[str] = Field(None, description="Organization UUID (required for B2B plans)")


class CreateOrderResponse(BaseModel):
    order_id:        str
    razorpay_key_id: str
    amount_paise:    int
    currency:        str
    plan_code:       str
    description:     str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id:     str
    razorpay_subscription_id: Optional[str] = None  # B2C subscription flow
    razorpay_order_id:       Optional[str] = None   # B2B order flow
    razorpay_signature:      str
    plan_code:               str
    org_id:                  Optional[str] = None   # B2B only


class StatusResponse(BaseModel):
    market:              str
    plan_code:           str
    subscription_status: str
    is_pro:              bool
    current_period_end:  Optional[datetime]
    razorpay_subscription_id: Optional[str]


# ── B2C Subscription ──────────────────────────────────────────────────────────

@router.post(
    "/create-subscription",
    response_model=CreateSubscriptionResponse,
    summary="Create Razorpay recurring subscription (B2C)",
)
async def create_subscription(
    body: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateSubscriptionResponse:
    """
    Creates (or retrieves existing) Razorpay Customer and Subscription for a
    B2C user.  The returned ``subscription_id`` should be passed to the
    Razorpay Checkout.js ``options.subscription_id`` field on the frontend.
    """
    if user.role in OFFICIAL_INSTITUTIONAL_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"User account has official role '{user.role}' with complimentary institutional access. Consumer subscriptions are only required for citizen accounts.",
        )

    plan_meta = _B2C_PLANS.get(body.plan_code)
    if not plan_meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown B2C plan_code '{body.plan_code}'. "
                   f"Valid plans: {', '.join(_B2C_PLANS.keys())}",
        )

    client = _get_razorpay_client()

    # 1. Create or retrieve Razorpay Customer
    if not user.razorpay_customer_id:
        try:
            customer = client.customer.create({
                "name":  user.full_name or user.email,
                "email": user.email,
            })
            user.razorpay_customer_id = customer["id"]
            await db.commit()
        except Exception as exc:
            logger.error("Failed to create Razorpay customer for user %s: %s", user.id, exc)
            raise HTTPException(status_code=500, detail="Failed to initialise payment customer.")

    razorpay_subscription_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_plan_id: Optional[str] = None

    # Try recurring e-mandate subscription if active on merchant account;
    # fallback smoothly to standard Order checkout (UPI, QR, Card, Netbanking)
    try:
        rz_plan = client.plan.create({
            "period":   plan_meta["period"],
            "interval": plan_meta["interval"],
            "item": {
                "name":     plan_meta["name"],
                "amount":   plan_meta["amount"],
                "currency": plan_meta["currency"],
            },
        })
        razorpay_plan_id = rz_plan["id"]

        rz_sub = client.subscription.create({
            "plan_id":          razorpay_plan_id,
            "customer_id":      user.razorpay_customer_id,
            "quantity":         1,
            "total_count":      120,  # max billing cycles (10 years)
            "customer_notify":  1,
            "notes": {
                "user_id":   str(user.id),
                "plan_code": body.plan_code,
                "source":    "digital_rakshak_b2c",
            },
        })
        razorpay_subscription_id = rz_sub["id"]
    except Exception as exc:
        logger.info("Subscriptions API not enabled on account (%s). Using standard Razorpay Order flow.", exc)
        rz_order = client.order.create({
            "amount":   plan_meta["amount"],
            "currency": plan_meta["currency"],
            "receipt":  f"rcpt_b2c_{uuid.uuid4().hex[:8]}",
            "notes": {
                "user_id":   str(user.id),
                "plan_code": body.plan_code,
                "source":    "digital_rakshak_b2c",
            },
        })
        razorpay_order_id = rz_order["id"]

    # 4. Record as pending subscription in DB
    pending_sub = Subscription(
        user_id=user.id,
        market=MarketSegment.B2C.value,
        plan_code=body.plan_code,
        status=SubscriptionStatus.TRIALING.value,
        razorpay_customer_id=user.razorpay_customer_id,
        razorpay_subscription_id=razorpay_subscription_id,
        razorpay_order_id=razorpay_order_id,
        razorpay_plan_id=razorpay_plan_id,
    )
    db.add(pending_sub)
    await db.commit()

    return CreateSubscriptionResponse(
        subscription_id=razorpay_subscription_id,
        order_id=razorpay_order_id,
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        plan_code=body.plan_code,
        amount_paise=plan_meta["amount"],
        currency=plan_meta["currency"],
    )


# ── B2B Order ─────────────────────────────────────────────────────────────────

@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    summary="Create Razorpay one-time order (B2B pilot / monthly plan)",
)
async def create_order(
    body: CreateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateOrderResponse:
    """
    Creates a Razorpay Order for B2B one-time or monthly subscription payments.
    The ``order_id`` is passed to Razorpay Checkout.js on the frontend.
    """
    plan_meta = _B2B_ORDERS.get(body.plan_code)
    if not plan_meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown B2B plan_code '{body.plan_code}'. "
                   f"Valid plans: {', '.join(_B2B_ORDERS.keys())}",
        )

    client = _get_razorpay_client()

    receipt = f"dr_b2b_{body.plan_code}_{uuid.uuid4().hex[:8]}"
    try:
        order = client.order.create({
            "amount":   plan_meta["amount"],
            "currency": plan_meta["currency"],
            "receipt":  receipt,
            "notes": {
                "plan_code": body.plan_code,
                "org_id":    body.org_id or "",
                "user_id":   str(user.id),
            },
        })
    except Exception as exc:
        logger.error("Failed to create Razorpay order: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create payment order.")

    return CreateOrderResponse(
        order_id=order["id"],
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        amount_paise=plan_meta["amount"],
        currency=plan_meta["currency"],
        plan_code=body.plan_code,
        description=plan_meta["name"],
    )


# ── Payment Verification ──────────────────────────────────────────────────────

@router.post("/verify-payment", summary="Verify Razorpay payment & activate subscription")
async def verify_payment(
    body: VerifyPaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verifies Razorpay HMAC-SHA256 signature and activates the subscription.

    Signature verification follows the Razorpay spec:
    * Subscription: ``HMAC(payment_id + "|" + subscription_id)``
    * Order:        ``HMAC(order_id + "|" + payment_id)``
    """
    gateway_configured = bool(
        settings.RAZORPAY_KEY_ID
        and settings.RAZORPAY_KEY_SECRET
        and not settings.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder")
        and not settings.RAZORPAY_KEY_SECRET.startswith("rzp_test_secret_placeholder")
    )

    is_sandbox_token = (
        (body.razorpay_subscription_id and body.razorpay_subscription_id.startswith("sub_sandbox"))
        or (body.razorpay_order_id and body.razorpay_order_id.startswith("order_sandbox"))
    )

    if gateway_configured and is_sandbox_token:
        raise HTTPException(
            status_code=400,
            detail="Sandbox payment IDs are not accepted when live Razorpay integration is active.",
        )

    is_sandbox = not gateway_configured

    if not is_sandbox:
        if not settings.RAZORPAY_KEY_SECRET:
            raise HTTPException(status_code=503, detail="Payment gateway not configured.")

        secret = settings.RAZORPAY_KEY_SECRET.encode()

        if body.razorpay_subscription_id:
            # B2C subscription flow
            message = f"{body.razorpay_payment_id}|{body.razorpay_subscription_id}".encode()
            expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
            sub_id = body.razorpay_subscription_id
        elif body.razorpay_order_id:
            # B2B order flow
            message = f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode()
            expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
            sub_id = None
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either razorpay_subscription_id or razorpay_order_id.",
            )

        if not hmac.compare_digest(expected, body.razorpay_signature):
            logger.warning("Payment verification failed for user %s — signature mismatch.", user.id)
            raise HTTPException(status_code=400, detail="Payment verification failed.")
    else:
        sub_id = body.razorpay_subscription_id
        logger.info("Sandbox payment verified for user %s plan %s", user.id, body.plan_code)


    # ── Activate subscription in DB ─────────────────────────────────────────
    is_b2c = body.plan_code in _B2C_PLANS
    now    = datetime.now(timezone.utc)

    if is_b2c:
        # Find pending subscription record
        sub = None
        if sub_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.razorpay_subscription_id == sub_id,
                )
            )
            sub = result.scalar_one_or_none()
        elif body.razorpay_order_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.razorpay_order_id == body.razorpay_order_id,
                )
            )
            sub = result.scalar_one_or_none()

        if sub:
            sub.status = SubscriptionStatus.ACTIVE.value
            sub.current_period_start = now
            sub.current_period_end   = now + timedelta(days=30)
            await db.commit()

        # Update User cached entitlement
        user.b2c_plan_code          = body.plan_code
        user.b2c_subscription_status = SubscriptionStatus.ACTIVE.value
        await db.commit()

    else:
        # B2B — create or update org subscription
        plan_meta = _B2B_ORDERS.get(body.plan_code, {})
        duration  = plan_meta.get("duration_days", 30)
        org_id    = uuid.UUID(body.org_id) if body.org_id else None

        b2b_sub = Subscription(
            user_id=user.id,
            org_id=org_id,
            market=MarketSegment.B2B.value,
            plan_code=body.plan_code,
            status=SubscriptionStatus.ACTIVE.value,
            razorpay_order_id=body.razorpay_order_id,
            current_period_start=now,
            current_period_end=now + timedelta(days=duration),
        )
        db.add(b2b_sub)
        await db.commit()

    logger.info(
        "Payment verified & subscription activated: user=%s plan=%s",
        user.id, body.plan_code,
    )
    return {"status": "success", "message": "Subscription activated.", "plan_code": body.plan_code}


# ── Razorpay Webhook ──────────────────────────────────────────────────────────

@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,  # Don't expose webhook URL in OpenAPI
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Receives and processes Razorpay webhook events.

    Events handled:
    * ``subscription.authenticated`` → plan activated (mandate confirmed)
    * ``subscription.charged``       → recurring charge succeeded
    * ``subscription.halted``        → payment failed repeatedly → downgrade
    * ``payment.failed``             → payment failed (informational)
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured.")

    body_bytes = await request.body()

    # Verify HMAC-SHA256 signature
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, x_razorpay_signature):
        logger.warning("Razorpay webhook signature mismatch — rejecting.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        event = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event_type = event.get("event", "")
    payload    = event.get("payload", {})

    logger.info("Razorpay webhook received: %s", event_type)

    if event_type in ("subscription.authenticated", "subscription.charged"):
        sub_entity = payload.get("subscription", {}).get("entity", {})
        rz_sub_id  = sub_entity.get("id")
        if rz_sub_id:
            result = await db.execute(
                select(Subscription).where(Subscription.razorpay_subscription_id == rz_sub_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = SubscriptionStatus.ACTIVE.value
                sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
                await db.commit()
                # Also update User cached entitlement if B2C
                if sub.user_id and sub.market == MarketSegment.B2C.value:
                    user_result = await db.execute(
                        select(User).where(User.id == sub.user_id)  # type: ignore[arg-type]
                    )
                    u = user_result.scalar_one_or_none()
                    if u:
                        u.b2c_plan_code          = sub.plan_code
                        u.b2c_subscription_status = SubscriptionStatus.ACTIVE.value
                        await db.commit()

    elif event_type == "subscription.halted":
        sub_entity = payload.get("subscription", {}).get("entity", {})
        rz_sub_id  = sub_entity.get("id")
        if rz_sub_id:
            result = await db.execute(
                select(Subscription).where(Subscription.razorpay_subscription_id == rz_sub_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = SubscriptionStatus.HALTED.value
                await db.commit()
                if sub.user_id and sub.market == MarketSegment.B2C.value:
                    user_result = await db.execute(
                        select(User).where(User.id == sub.user_id)  # type: ignore[arg-type]
                    )
                    u = user_result.scalar_one_or_none()
                    if u:
                        u.b2c_plan_code          = "b2c_free"
                        u.b2c_subscription_status = SubscriptionStatus.HALTED.value
                        await db.commit()

    elif event_type == "payment.failed":
        logger.warning("payment.failed webhook received: %s", payload)

    return {"status": "ok"}


# ── Subscription Status ───────────────────────────────────────────────────────

@router.get("/status", response_model=StatusResponse, summary="Get current subscription status")
async def get_subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    if user.role in OFFICIAL_INSTITUTIONAL_ROLES:
        return StatusResponse(
            market="institutional",
            plan_code=f"official_{user.role}",
            subscription_status=SubscriptionStatus.ACTIVE.value,
            is_pro=True,
            current_period_end=None,
            razorpay_subscription_id=None,
        )

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.market  == MarketSegment.B2C.value,
        ).order_by(Subscription.created_at.desc()).limit(1)
    )
    sub = result.scalar_one_or_none()

    plan_code   = user.b2c_plan_code or "b2c_free"
    sub_status  = user.b2c_subscription_status or "active"
    is_pro      = plan_code != "b2c_free" and sub_status == SubscriptionStatus.ACTIVE.value

    return StatusResponse(
        market=MarketSegment.B2C.value,
        plan_code=plan_code,
        subscription_status=sub_status,
        is_pro=is_pro,
        current_period_end=sub.current_period_end if sub else None,
        razorpay_subscription_id=sub.razorpay_subscription_id if sub else None,
    )
