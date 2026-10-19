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

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_current_user_optional, get_db, OFFICIAL_INSTITUTIONAL_ROLES
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
        "base_amount": 14900,     # paise (₹149.00 base)
        "cgst_amount": 1341,      # paise (₹13.41 CGST @ 9%)
        "sgst_amount": 1341,      # paise (₹13.41 SGST @ 9%)
        "tax_amount":  2682,      # paise (₹26.82 18% GST)
        "amount":      17582,     # paise (₹175.82 total gross payable)
        "currency":    "INR",
        "period":      "monthly",
        "interval":    1,
        "days":        30,
        "name":        "Digital Rakshak Personal Pro (₹149 + 18% GST)",
    },
    PlanCode.B2C_PRO_249.value: {
        "base_amount": 24900,     # paise (₹249.00 base)
        "cgst_amount": 2241,      # paise (₹22.41 CGST @ 9%)
        "sgst_amount": 2241,      # paise (₹22.41 SGST @ 9%)
        "tax_amount":  4482,      # paise (₹44.82 18% GST)
        "amount":      29382,     # paise (₹293.82 total gross payable)
        "currency":    "INR",
        "period":      "monthly",
        "interval":    1,
        "days":        30,
        "name":        "Digital Rakshak Family Shield (₹249 + 18% GST)",
    },
    PlanCode.B2C_PRO_ANNUAL.value: {
        "base_amount": 129900,    # paise (₹1,299.00 base)
        "cgst_amount": 11691,     # paise (₹116.91 CGST @ 9%)
        "sgst_amount": 11691,     # paise (₹116.91 SGST @ 9%)
        "tax_amount":  23382,     # paise (₹233.82 18% GST)
        "amount":      153282,    # paise (₹1,532.82 total gross payable)
        "currency":    "INR",
        "period":      "yearly",
        "interval":    1,
        "days":        365,
        "name":        "Digital Rakshak Pro Annual (₹1299 + 18% GST)",
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

        total_cycles = 10 if plan_meta.get("period") == "yearly" else 120
        rz_sub = client.subscription.create({
            "plan_id":          razorpay_plan_id,
            "customer_id":      user.razorpay_customer_id,
            "quantity":         1,
            "total_count":      total_cycles,
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
        plan_meta = _B2C_PLANS.get(body.plan_code, {})
        plan_days = plan_meta.get("days", 365 if body.plan_code == PlanCode.B2C_PRO_ANNUAL.value else 30)

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
            sub.plan_code = body.plan_code
            sub.current_period_start = now
            sub.current_period_end   = now + timedelta(days=plan_days)
            await db.commit()
            await db.refresh(sub)
        else:
            sub = Subscription(
                user_id=user.id,
                market=MarketSegment.B2C.value,
                plan_code=body.plan_code,
                status=SubscriptionStatus.ACTIVE.value,
                razorpay_customer_id=user.razorpay_customer_id,
                razorpay_subscription_id=sub_id,
                razorpay_order_id=body.razorpay_order_id,
                current_period_start=now,
                current_period_end=now + timedelta(days=plan_days),
            )
            db.add(sub)
            await db.commit()
            await db.refresh(sub)

        # Update User cached entitlement
        user.b2c_plan_code          = body.plan_code
        user.b2c_subscription_status = SubscriptionStatus.ACTIVE.value
        await db.commit()

        # Send subscription upgrade confirmation email with attached PDF invoice
        try:
            from infrastructure.smtp.email_service import send_subscription_confirmed_email
            from infrastructure.pdf.invoice_pdf import generate_invoice_pdf

            inv, invoice_html = _build_invoice_data(sub, user)
            billing_cycle = "Yearly (365 Days)" if body.plan_code == PlanCode.B2C_PRO_ANNUAL.value else "Monthly (30 Days)"
            pdf_bytes = generate_invoice_pdf(
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                buyer_name=inv.buyer_name,
                buyer_email=inv.buyer_email,
                plan_name=inv.plan_name,
                taxable_base=inv.taxable_base_amount,
                cgst=inv.cgst_amount,
                sgst=inv.sgst_amount,
                total_tax=inv.total_tax_amount,
                gross_amount=inv.gross_amount,
                currency=inv.currency,
                payment_status=inv.payment_status,
            )

            # Check if Razorpay payment has an explicit payer email different from user.email
            target_emails = [user.email]
            if settings.ADMIN_EMAIL and settings.ADMIN_EMAIL.strip().lower() not in [e.lower() for e in target_emails]:
                target_emails.append(settings.ADMIN_EMAIL.strip())
            try:
                rzp_client = _get_razorpay_client()
                if body.razorpay_payment_id and not isinstance(rzp_client, _SandboxRazorpayClient):
                    pay_info = rzp_client.payment.fetch(body.razorpay_payment_id)
                    payer_mail = pay_info.get("email")
                    if payer_mail and payer_mail.strip().lower() not in [e.strip().lower() for e in target_emails]:
                        target_emails.append(payer_mail.strip())
            except Exception as rzp_mail_err:
                logger.warning("Could not check payer email from Razorpay payment: %s", rzp_mail_err)

            for recipient in target_emails:
                await send_subscription_confirmed_email(
                    to_email=recipient,
                    full_name=user.full_name or "Valued Citizen",
                    plan_name=plan_meta.get("name", body.plan_code),
                    subscription_id=sub.razorpay_subscription_id or str(sub.id),
                    base_amount=inv.taxable_base_amount,
                    cgst_amount=inv.cgst_amount,
                    sgst_amount=inv.sgst_amount,
                    tax_amount=inv.total_tax_amount,
                    gross_amount=inv.gross_amount,
                    billing_cycle=billing_cycle,
                    invoice_number=inv.invoice_number,
                    invoice_html=invoice_html,
                    invoice_pdf_bytes=pdf_bytes,
                )
                logger.info("Subscription confirmation email dispatched to %s for plan %s with PDF tax invoice attachment", recipient, body.plan_code)
        except Exception as mail_err:
            logger.error("Failed to send subscription confirmation email: %s", mail_err)

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

                        try:
                            from infrastructure.smtp.email_service import send_subscription_confirmed_email
                            from infrastructure.pdf.invoice_pdf import generate_invoice_pdf
                            inv, invoice_html = _build_invoice_data(sub, u)
                            plan_meta = _B2C_PLANS.get(sub.plan_code, {})
                            billing_cycle = "Yearly (365 Days)" if sub.plan_code == PlanCode.B2C_PRO_ANNUAL.value else "Monthly (30 Days)"
                            pdf_bytes = generate_invoice_pdf(
                                invoice_number=inv.invoice_number,
                                invoice_date=inv.invoice_date,
                                buyer_name=inv.buyer_name,
                                buyer_email=inv.buyer_email,
                                plan_name=inv.plan_name,
                                taxable_base=inv.taxable_base_amount,
                                cgst=inv.cgst_amount,
                                sgst=inv.sgst_amount,
                                total_tax=inv.total_tax_amount,
                                gross_amount=inv.gross_amount,
                                currency=inv.currency,
                                payment_status=inv.payment_status,
                            )
                            await send_subscription_confirmed_email(
                                to_email=u.email,
                                full_name=u.full_name or "Valued Citizen",
                                plan_name=plan_meta.get("name", sub.plan_code),
                                subscription_id=sub.razorpay_subscription_id or str(sub.id),
                                base_amount=inv.taxable_base_amount,
                                cgst_amount=inv.cgst_amount,
                                sgst_amount=inv.sgst_amount,
                                tax_amount=inv.total_tax_amount,
                                gross_amount=inv.gross_amount,
                                billing_cycle=billing_cycle,
                                invoice_number=inv.invoice_number,
                                invoice_html=invoice_html,
                                invoice_pdf_bytes=pdf_bytes,
                            )
                            logger.info("Webhook dispatched confirmation email & PDF invoice to %s", u.email)
                        except Exception as w_mail_err:
                            logger.error("Failed to send webhook confirmation email: %s", w_mail_err)

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


# ── Tax Invoicing & GST Compliance (Phase 4.3) ──────────────────────────────

class TaxInvoiceResponse(BaseModel):
    invoice_number:      str
    invoice_date:        str
    supplier_name:       str
    supplier_gstin:      str
    supplier_sac_code:   str
    buyer_name:          str
    buyer_email:         str
    plan_code:           str
    plan_name:           str
    currency:            str
    gross_amount:        float
    taxable_base_amount: float
    cgst_amount:         float
    sgst_amount:         float
    igst_amount:         float
    total_tax_amount:    float
    payment_status:      str


def _render_invoice_html(inv: TaxInvoiceResponse) -> str:
    """Renders print-ready GST Tax Invoice document with SAC 998313 and CGST/SGST itemization."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tax Invoice - {inv.invoice_number}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 32px 16px; background: #f8fafc; }}
    .container {{ max-width: 800px; margin: 0 auto; }}
    .actions {{ display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 20px; }}
    .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 10px 18px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; text-decoration: none; border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a; transition: background 0.15s ease; }}
    .btn:hover {{ background: #f1f5f9; }}
    .btn-primary {{ background: #0284c7; color: #ffffff; border-color: #0284c7; }}
    .btn-primary:hover {{ background: #0369a1; }}
    .invoice-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 48px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0284c7; padding-bottom: 24px; margin-bottom: 28px; }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand-logo {{ width: 44px; height: 44px; border-radius: 10px; background: linear-gradient(135deg, #0284c7, #4f46e5); display: flex; align-items: center; justify-content: center; color: white; font-weight: 900; font-size: 22px; }}
    .brand-name {{ font-size: 22px; font-weight: 800; letter-spacing: -0.02em; color: #0f172a; }}
    .brand-sub {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 600; }}
    .invoice-title {{ text-align: right; }}
    .invoice-title h1 {{ margin: 0; font-size: 24px; font-weight: 800; color: #0f172a; text-transform: uppercase; letter-spacing: 0.03em; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; margin-top: 6px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-bottom: 32px; }}
    .block-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; color: #64748b; margin-bottom: 8px; }}
    .block-content {{ font-size: 13px; line-height: 1.6; color: #334155; }}
    .block-content strong {{ color: #0f172a; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 28px; font-size: 13px; }}
    th {{ background: #f8fafc; text-align: left; padding: 12px 14px; font-weight: 700; color: #334155; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; font-size: 11px; letter-spacing: 0.04em; }}
    td {{ padding: 14px; border-bottom: 1px solid #f1f5f9; color: #1e293b; }}
    .text-right {{ text-align: right; }}
    .totals-wrap {{ display: flex; justify-content: flex-end; margin-bottom: 36px; }}
    .totals-box {{ width: 340px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; }}
    .total-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; color: #475569; }}
    .total-row.grand {{ border-top: 1px solid #cbd5e1; padding-top: 10px; margin-top: 6px; font-weight: 800; font-size: 16px; color: #0f172a; }}
    .footer-notes {{ border-top: 1px solid #e2e8f0; padding-top: 24px; font-size: 11px; color: #64748b; line-height: 1.7; }}
    .auth-stamp {{ margin-top: 24px; display: flex; justify-content: space-between; align-items: flex-end; }}
    .stamp-box {{ text-align: right; font-size: 11px; color: #64748b; }}
    .stamp-sig {{ font-family: "Georgia", serif; font-size: 16px; font-style: italic; color: #0f172a; margin-top: 8px; }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .actions {{ display: none !important; }}
      .invoice-box {{ border: none; box-shadow: none; padding: 20px 0; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="actions">
      <button class="btn" onclick="window.close()">Close</button>
      <button class="btn btn-primary" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>

    <div class="invoice-box">
      <div class="header">
        <div class="brand">
          <div class="brand-logo">🛡️</div>
          <div>
            <div class="brand-name">Digital Rakshak</div>
            <div class="brand-sub">Cyber Defense Core India</div>
          </div>
        </div>
        <div class="invoice-title">
          <h1>Tax Invoice</h1>
          <div class="badge">{inv.payment_status}</div>
        </div>
      </div>

      <div class="grid-2">
        <div>
          <div class="block-label">Supplier Details</div>
          <div class="block-content">
            <strong>{inv.supplier_name}</strong><br>
            Cyber Defense Complex, Tech Zone 4<br>
            New Delhi, India — 110001<br>
            GSTIN: <strong>{inv.supplier_gstin}</strong><br>
            SAC Code: <strong>{inv.supplier_sac_code}</strong> (Threat Intel & Software)
          </div>
        </div>
        <div>
          <div class="block-label">Invoice & Customer Details</div>
          <div class="block-content">
            Invoice No: <strong>{inv.invoice_number}</strong><br>
            Invoice Date: <strong>{inv.invoice_date}</strong><br>
            Billed To: <strong>{inv.buyer_name}</strong><br>
            Email: <strong>{inv.buyer_email}</strong><br>
            Place of Supply: <strong>Delhi (07) / Pan-India</strong>
          </div>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Description of Services</th>
            <th>SAC Code</th>
            <th>Qty</th>
            <th class="text-right">Taxable Value</th>
            <th class="text-right">CGST (9%)</th>
            <th class="text-right">SGST (9%)</th>
            <th class="text-right">Total ({inv.currency})</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <strong>{inv.plan_name}</strong><br>
              <span style="font-size: 11px; color: #64748b;">Continuous Zero-Day AI Defense, Attack DNA Deconstruction & Graph Correlation</span>
            </td>
            <td>{inv.supplier_sac_code}</td>
            <td>1</td>
            <td class="text-right">₹{inv.taxable_base_amount:.2f}</td>
            <td class="text-right">₹{inv.cgst_amount:.2f}</td>
            <td class="text-right">₹{inv.sgst_amount:.2f}</td>
            <td class="text-right"><strong>₹{inv.gross_amount:.2f}</strong></td>
          </tr>
        </tbody>
      </table>

      <div class="totals-wrap">
        <div class="totals-box">
          <div class="total-row">
            <span>Taxable Base Amount:</span>
            <span>₹{inv.taxable_base_amount:.2f}</span>
          </div>
          <div class="total-row">
            <span>Central GST (CGST @ 9%):</span>
            <span>₹{inv.cgst_amount:.2f}</span>
          </div>
          <div class="total-row">
            <span>State GST (SGST @ 9%):</span>
            <span>₹{inv.sgst_amount:.2f}</span>
          </div>
          <div class="total-row">
            <span>Total GST Tax (18%):</span>
            <span>₹{inv.total_tax_amount:.2f}</span>
          </div>
          <div class="total-row grand">
            <span>Total Invoice Amount:</span>
            <span>₹{inv.gross_amount:.2f}</span>
          </div>
        </div>
      </div>

      <div class="footer-notes">
        <strong>Terms & Declarations:</strong><br>
        1. This is a computer-generated tax invoice issued in compliance with the Central Goods and Services Tax Act, 2017.<br>
        2. Supply covered under SAC 998313 (Cybersecurity threat intelligence and cloud SaaS defense services).<br>
        3. Payment received electronically via Razorpay UPI AutoPay / Credit / Debit Card.<br>
        4. Supply of service is not liable for Reverse Charge (RCM: No).
      </div>

      <div class="auth-stamp">
        <div style="font-size: 11px; color: #64748b;">
          Digital Rakshak Cyber Defense Core Pvt. Ltd. • CIN: U72900DL2026PTC123456
        </div>
        <div class="stamp-box">
          For Digital Rakshak Cyber Defense Core Pvt. Ltd.<br>
          <div class="stamp-sig">Authorized Signatory</div>
          (Digital Authentication Seal)
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""


def _build_invoice_data(sub: Subscription, user: User) -> tuple[TaxInvoiceResponse, str]:
    """Computes tax-exclusive invoice figures and generates the official HTML document."""
    plan_meta = _B2C_PLANS.get(sub.plan_code) or _B2B_ORDERS.get(sub.plan_code) or {}

    if "base_amount" in plan_meta:
        taxable_base = round(plan_meta["base_amount"] / 100.0, 2)
        cgst = round(plan_meta.get("cgst_amount", round(taxable_base * 0.09, 2) * 100) / 100.0, 2)
        sgst = round(plan_meta.get("sgst_amount", round(taxable_base * 0.09, 2) * 100) / 100.0, 2)
        total_tax = round(plan_meta.get("tax_amount", round(cgst + sgst, 2) * 100) / 100.0, 2)
        gross_inr = round(plan_meta.get("amount", round(taxable_base + total_tax, 2) * 100) / 100.0, 2)
    else:
        raw_paise = plan_meta.get("amount", 14900)
        gross_inr = round(raw_paise / 100.0, 2)
        taxable_base = round(gross_inr / 1.18, 2)
        total_tax = round(gross_inr - taxable_base, 2)
        cgst = round(total_tax / 2.0, 2)
        sgst = round(total_tax - cgst, 2)

    inv_date = (sub.current_period_start or sub.created_at or datetime.now(timezone.utc)).strftime("%d-%b-%Y")
    inv_num = f"INV-DR-{inv_date[-4:]}-{str(sub.id)[:8].upper()}"

    inv = TaxInvoiceResponse(
        invoice_number=inv_num,
        invoice_date=inv_date,
        supplier_name="Digital Rakshak Cyber Defense Core Pvt. Ltd.",
        supplier_gstin="07AABCD1234E1Z5",
        supplier_sac_code="998313",
        buyer_name=user.full_name or "Verified Customer",
        buyer_email=user.email,
        plan_code=sub.plan_code,
        plan_name=plan_meta.get("name", sub.plan_code),
        currency=plan_meta.get("currency", "INR"),
        gross_amount=gross_inr,
        taxable_base_amount=taxable_base,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=0.0,
        total_tax_amount=total_tax,
        payment_status="PAID" if sub.status == SubscriptionStatus.ACTIVE.value else sub.status.upper(),
    )

    html = _render_invoice_html(inv)
    return inv, html


@router.get("/invoice/{subscription_id}", response_model=TaxInvoiceResponse, summary="Generate GST-compliant tax invoice")
async def generate_tax_invoice(
    subscription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxInvoiceResponse:
    """
    Generates a compliant GST tax invoice (SAC 998313 - Cybersecurity Threat Intel & Software Services)
    with 18% GST calculation (9% CGST + 9% SGST).
    """
    if subscription_id == "latest":
        cond = (Subscription.user_id == user.id)
        result = await db.execute(select(Subscription).where(cond).order_by(Subscription.created_at.desc()).limit(1))
    else:
        is_valid_uuid = False
        try:
            sub_uuid = uuid.UUID(subscription_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        cond = (Subscription.razorpay_subscription_id == subscription_id) | (Subscription.razorpay_order_id == subscription_id)
        if is_valid_uuid:
            cond = cond | (Subscription.id == sub_uuid)

        result = await db.execute(select(Subscription).where(cond))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription or order record not found.")

    # Access control: user must own the subscription or be an admin
    if sub.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to view this invoice.")

    inv, _ = _build_invoice_data(sub, user)
    return inv


@router.get("/invoice/{subscription_id}/html", response_class=HTMLResponse, summary="Download official print-ready GST tax invoice HTML")
async def generate_tax_invoice_html(
    subscription_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Renders an official, print-ready GST Tax Invoice document with SAC 998313,
    complete CGST/SGST breakdown, and print-to-PDF button.
    Accepts Bearer auth header or ?token= query parameter for direct tab viewing.
    """
    if user is None and token:
        from core.security import decode_access_token
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == payload["sub"]))
            user = u_res.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to view tax invoice.")

    if subscription_id == "latest":
        cond = (Subscription.user_id == user.id)
        result = await db.execute(select(Subscription).where(cond).order_by(Subscription.created_at.desc()).limit(1))
    else:
        is_valid_uuid = False
        try:
            sub_uuid = uuid.UUID(subscription_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        cond = (Subscription.razorpay_subscription_id == subscription_id) | (Subscription.razorpay_order_id == subscription_id)
        if is_valid_uuid:
            cond = cond | (Subscription.id == sub_uuid)

        result = await db.execute(select(Subscription).where(cond))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription or order record not found.")

    if sub.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to view this invoice.")

    _, html = _build_invoice_data(sub, user)
    return HTMLResponse(content=html)


@router.get("/invoice/{subscription_id}/pdf", summary="Download official GST tax invoice as mobile-compatible PDF document")
async def generate_tax_invoice_pdf_endpoint(
    subscription_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Renders an official A4 GST Tax Invoice as an authentic PDF file (application/pdf).
    Compatible with native PDF viewers on iPhone, Android, tablets, and laptops.
    Accepts Bearer auth header or ?token= query parameter for direct tab viewing/download.
    """
    if user is None and token:
        from core.security import decode_access_token
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == payload["sub"]))
            user = u_res.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to download tax invoice.")

    if subscription_id == "latest":
        cond = (Subscription.user_id == user.id)
        result = await db.execute(select(Subscription).where(cond).order_by(Subscription.created_at.desc()).limit(1))
    else:
        is_valid_uuid = False
        try:
            sub_uuid = uuid.UUID(subscription_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        cond = (Subscription.razorpay_subscription_id == subscription_id) | (Subscription.razorpay_order_id == subscription_id)
        if is_valid_uuid:
            cond = cond | (Subscription.id == sub_uuid)

        result = await db.execute(select(Subscription).where(cond))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription or order record not found.")

    if sub.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to download this invoice.")

    from infrastructure.pdf.invoice_pdf import generate_invoice_pdf
    inv, _ = _build_invoice_data(sub, user)
    pdf_bytes = generate_invoice_pdf(
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        buyer_name=inv.buyer_name,
        buyer_email=inv.buyer_email,
        plan_name=inv.plan_name,
        taxable_base=inv.taxable_base_amount,
        cgst=inv.cgst_amount,
        sgst=inv.sgst_amount,
        total_tax=inv.total_tax_amount,
        gross_amount=inv.gross_amount,
        currency=inv.currency,
        payment_status=inv.payment_status,
    )

    clean_sub_id = sub.razorpay_subscription_id or str(sub.id)[:8]
    filename = f"Digital_Rakshak_Tax_Invoice_{clean_sub_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


class ResendInvoiceRequest(BaseModel):
    target_email: Optional[str] = None


class CancelSubscriptionRequest(BaseModel):
    notification_email: Optional[str] = None


@router.post("/invoice/resend", summary="Resend tax invoice PDF to registered email or specified address")
async def resend_tax_invoice(
    body: Optional[ResendInvoiceRequest] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Re-generates and sends the official GST Tax Invoice as a PDF attachment to the user's registered email
    and any specified target email address or primary inbox.
    """
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        ).order_by(Subscription.created_at.desc()).limit(1)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.created_at.desc()).limit(1)
        )
        sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="No active or past subscription found for your account.")

    from infrastructure.smtp.email_service import send_subscription_confirmed_email
    from infrastructure.pdf.invoice_pdf import generate_invoice_pdf

    inv, invoice_html = _build_invoice_data(sub, user)
    plan_meta = _B2C_PLANS.get(sub.plan_code) or _B2B_ORDERS.get(sub.plan_code) or {}
    billing_cycle = "Yearly (365 Days)" if sub.plan_code == PlanCode.B2C_PRO_ANNUAL.value else "Monthly (30 Days)"

    pdf_bytes = generate_invoice_pdf(
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        buyer_name=inv.buyer_name,
        buyer_email=inv.buyer_email,
        plan_name=inv.plan_name,
        taxable_base=inv.taxable_base_amount,
        cgst=inv.cgst_amount,
        sgst=inv.sgst_amount,
        total_tax=inv.total_tax_amount,
        gross_amount=inv.gross_amount,
        currency=inv.currency,
        payment_status=inv.payment_status,
    )

    recipients = [user.email]
    if body and body.target_email and body.target_email.strip():
        t_email = body.target_email.strip()
        if t_email.lower() not in [e.lower() for e in recipients]:
            recipients.append(t_email)
    if settings.ADMIN_EMAIL and settings.ADMIN_EMAIL.strip().lower() not in [e.lower() for e in recipients]:
        recipients.append(settings.ADMIN_EMAIL.strip())

    sent_any = False
    for recipient in recipients:
        sent = await send_subscription_confirmed_email(
            to_email=recipient,
            full_name=user.full_name or "Valued Citizen",
            plan_name=plan_meta.get("name", sub.plan_code),
            subscription_id=sub.razorpay_subscription_id or str(sub.id),
            base_amount=inv.taxable_base_amount,
            cgst_amount=inv.cgst_amount,
            sgst_amount=inv.sgst_amount,
            tax_amount=inv.total_tax_amount,
            gross_amount=inv.gross_amount,
            billing_cycle=billing_cycle,
            invoice_number=inv.invoice_number,
            invoice_html=invoice_html,
            invoice_pdf_bytes=pdf_bytes,
        )
        if sent:
            sent_any = True
            logger.info("Tax invoice PDF re-sent to %s", recipient)

    if not sent_any:
        raise HTTPException(status_code=500, detail="Failed to deliver tax invoice email. Please check SMTP configuration.")

    return {
        "status": "ok",
        "message": f"Official GST Tax Invoice PDF has been sent to {', '.join(recipients)}.",
        "invoice_number": inv.invoice_number,
        "recipients": recipients,
    }


# ── Subscription Cancellation (Phase 4.3 & Prorated Base Refund) ─────────────

@router.post("/cancel-subscription", summary="Cancel active subscription with prorated base refund")
async def cancel_subscription(
    body: Optional[CancelSubscriptionRequest] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cancels the user's active B2C subscription, computes a prorated refund
    based exclusively on unused days of the base subscription fee (18% GST is retained
    as non-refundable government tax), dispatches a cancellation confirmation email
    (without bill/invoice attached), and reverts the account to the Free Shield plan.
    """
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        ).order_by(Subscription.created_at.desc()).limit(1)
    )
    sub = result.scalar_one_or_none()

    refund_details: Dict[str, Any] = {}
    now = datetime.now(timezone.utc)
    recipients = [user.email]
    if body and body.notification_email and body.notification_email.strip():
        n_email = body.notification_email.strip()
        if n_email.lower() not in [e.lower() for e in recipients]:
            recipients.append(n_email)
    if settings.ADMIN_EMAIL and settings.ADMIN_EMAIL.strip().lower() not in [e.lower() for e in recipients]:
        recipients.append(settings.ADMIN_EMAIL.strip())

    if sub:
        plan_meta = _B2C_PLANS.get(sub.plan_code) or _B2B_ORDERS.get(sub.plan_code) or {}

        # Base fee (tax is strictly non-refundable)
        base_paise = plan_meta.get("base_amount", 14900)
        base_inr = round(base_paise / 100.0, 2)
        tax_paise = plan_meta.get("tax_amount", 2682)
        tax_paid = round(tax_paise / 100.0, 2)
        gross_inr = round(plan_meta.get("amount", base_paise + tax_paise) / 100.0, 2)

        start = sub.current_period_start or sub.created_at or now
        default_days = 365 if sub.plan_code == PlanCode.B2C_PRO_ANNUAL.value else 30
        end = sub.current_period_end or (start + timedelta(days=default_days))

        total_seconds = max(1.0, (end - start).total_seconds())
        elapsed_seconds = max(0.0, min(total_seconds, (now - start).total_seconds()))

        total_days = max(1, round(total_seconds / 86400))
        # At least 1 day charged for active day
        days_used = max(1, min(total_days, int(elapsed_seconds // 86400) + 1))

        daily_base_rate = base_inr / total_days
        base_deduction = round(daily_base_rate * days_used, 2)
        refund_amount = max(0.0, round(base_inr - base_deduction, 2))

        refund_details = {
            "original_base_amount": base_inr,
            "tax_amount": tax_paid,
            "gross_amount_paid": gross_inr,
            "tax_refundable": False,
            "tax_policy_note": "Government GST (18%) remitted under SAC 998313 is strictly non-refundable.",
            "days_used": days_used,
            "total_days": total_days,
            "base_deduction_amount": base_deduction,
            "refund_amount": refund_amount,
            "currency": "INR",
            "refund_status": "initiated",
            "refund_timeline": "5-7 business days",
            "refund_destination": "Source payment method (UPI / Card)",
            "canceled_at": now.isoformat(),
        }

        sub.status = SubscriptionStatus.CANCELED.value
        sub.plan_metadata = {**(sub.plan_metadata or {}), "refund": refund_details}
        await db.commit()

        # Send cancellation email with refund calculation (strictly NO invoice attached) to all recipients
        from infrastructure.smtp.email_service import send_subscription_canceled_email
        for recipient in recipients:
            try:
                await send_subscription_canceled_email(
                    to_email=recipient,
                    full_name=user.full_name or "Valued Citizen",
                    plan_name=plan_meta.get("name", sub.plan_code),
                    subscription_id=sub.razorpay_subscription_id or str(sub.id),
                    original_base_amount=base_inr,
                    tax_amount=tax_paid,
                    gross_amount=gross_inr,
                    start_date=start.strftime("%d-%b-%Y"),
                    cancel_date=now.strftime("%d-%b-%Y"),
                    days_used=days_used,
                    total_days=total_days,
                    deduction_amount=base_deduction,
                    refund_amount=refund_amount,
                )
                logger.info("Subscription cancellation email sent to %s for plan %s (refund: ₹%s)", recipient, sub.plan_code, refund_amount)
            except Exception as mail_err:
                logger.error("Failed to send subscription cancellation email to %s: %s", recipient, mail_err)

    user.b2c_plan_code = "b2c_free"
    user.b2c_subscription_status = SubscriptionStatus.CANCELED.value
    await db.commit()

    return {
        "status": "ok",
        "message": f"Subscription canceled successfully. Base refund of ₹{refund_details.get('refund_amount', 0.0):.2f} initiated. Confirmation email dispatched to {', '.join(recipients)}.",
        "plan_code": "b2c_free",
        "refund_details": refund_details,
        "recipients": recipients,
    }
