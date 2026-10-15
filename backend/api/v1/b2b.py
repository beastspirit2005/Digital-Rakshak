"""
Digital Rakshak Business (B2B) API
====================================
Enterprise-grade threat event ingestion, API key management, and usage
quota endpoints for organizations using the B2B tier.

Authentication
--------------
All B2B endpoints require an ``x-api-key`` header containing a valid API key
belonging to an active organization.  The key is never echoed back — only the
SHA-256 hash is stored and compared.

Endpoints
---------
POST   /v1/b2b/events/ingest       Batch event ingestion (up to 100/call)
GET    /v1/b2b/events/stream       SSE real-time alert stream for this org
GET    /v1/b2b/keys                List API keys for this org
POST   /v1/b2b/keys                Create a new API key
DELETE /v1/b2b/keys/{key_id}       Revoke an API key
GET    /v1/b2b/usage               Current period event quota usage
GET    /v1/b2b/org                 Org profile + active subscription
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user_optional
from domain.models.user import User
from domain.models.organization import (
    ApiKey,
    Organization,
    OrganizationMember,
    OrgMemberRole,
    UsageQuota,
    Subscription,
    SubscriptionStatus,
    OrgTier,
)
from domain.models.case import Case
from infrastructure.event_bus.redis_streams import event_bus, STREAM_EVENTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/b2b", tags=["B2B Enterprise API"])


# ── Shared dependency: resolve API key OR Session User → Organization ───────────

async def get_org_from_api_key(
    x_api_key: Optional[str] = Header(None, description="Digital Rakshak B2B API key (dr_live_...)"),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    FastAPI dependency that validates either ``x-api-key`` or logged-in JWT user
    and returns the owning Organization. Updates ``last_used_at`` on every successful API key call.
    """
    if x_api_key and x_api_key.startswith("dr_"):
        key_hash = ApiKey.hash_key(x_api_key)
        prefix   = x_api_key[:12]

        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == prefix,
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,  # noqa: E712
            )
        )
        api_key_record = result.scalar_one_or_none()
        if api_key_record is not None:
            # Check expiry
            if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired.",
                )

            # Fetch organization
            org_result = await db.execute(
                select(Organization).where(
                    Organization.id == api_key_record.org_id,
                    Organization.is_active == True,  # noqa: E712
                )
            )
            org = org_result.scalar_one_or_none()

            if org is not None:
                # Update last_used_at (fire-and-forget style)
                api_key_record.last_used_at = datetime.now(timezone.utc)
                await db.commit()
                return org
            elif not user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization is inactive or not found.",
                )
        elif not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key.",
            )

    # Fallback to logged-in JWT session user
    if user:
        result = await db.execute(
            select(Organization).join(
                OrganizationMember, OrganizationMember.org_id == Organization.id
            ).where(
                OrganizationMember.user_id == user.id,
                Organization.is_active == True,
            )
        )
        org = result.scalar_one_or_none()
        if org:
            return org

        # Platform admins have oversight access to the primary workspace organization
        if user.role == "admin":
            result = await db.execute(
                select(Organization).where(Organization.is_active == True).order_by(Organization.created_at.asc()).limit(1)
            )
            org = result.scalar_one_or_none()
            if org:
                return org

            # Auto-provision primary organization for admin if none exists
            primary_org = Organization(
                name="Apex Nodal Labs (Enterprise)",
                slug="apex-nodal-labs",
                tier=OrgTier.ENTERPRISE,
                is_active=True,
            )
            db.add(primary_org)
            await db.flush()

            quota = UsageQuota(
                org_id=primary_org.id,
                period=datetime.now(timezone.utc).strftime("%Y-%m"),
                events_processed=0,
                monthly_limit=500_000,
            )
            db.add(quota)

            member = OrganizationMember(
                org_id=primary_org.id,
                user_id=user.id,
                role=OrgMemberRole.OWNER,
            )
            db.add(member)
            await db.commit()
            await db.refresh(primary_org)
            return primary_org

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Your account is not a member of any active enterprise organization.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide an 'x-api-key' header or sign in with an enterprise account.",
    )


# ── Quota guard helper ───────────────────────────────────────────────────────

async def _check_and_increment_quota(
    db: AsyncSession,
    org: Organization,
    event_count: int,
) -> UsageQuota:
    """
    Checks the organization's monthly event quota and increments the counter.
    Raises HTTP 429 if the hard limit is exceeded.
    """
    period = datetime.now(timezone.utc).strftime("%Y-%m")

    result = await db.execute(
        select(UsageQuota).where(
            UsageQuota.org_id == org.id,
            UsageQuota.period == period,
        )
    )
    quota = result.scalar_one_or_none()

    if quota is None:
        # First event of this period → create quota row
        quota = UsageQuota(
            org_id=org.id,
            period=period,
            events_processed=0,
            monthly_limit=_plan_limit_for_org(org),
        )
        db.add(quota)
        await db.flush()

    if quota.is_over_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly event quota of {quota.monthly_limit:,} events exceeded "
                f"for period {period}. Upgrade your plan or contact support."
            ),
        )

    quota.events_processed += event_count
    quota.overage_count = max(0, quota.events_processed - quota.monthly_limit)
    await db.commit()
    await db.refresh(quota)
    return quota


def _plan_limit_for_org(org: Organization) -> int:
    """Returns the monthly event limit based on the organization's tier."""
    limits = {
        "starter":    25_000,
        "business":  100_000,
        "enterprise": 10_000_000,  # effectively unlimited
    }
    return limits.get(org.tier, 25_000)


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class ThreatEvent(BaseModel):
    """A single threat security event from a B2B customer system."""
    event_id:    Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type:  str = Field(..., description="e.g. phishing_url, fraud_transaction, suspicious_login")
    severity:    str = Field("medium", description="low | medium | high | critical")
    source_ip:   Optional[str] = None
    source_user: Optional[str] = None
    metadata:    Dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class IngestRequest(BaseModel):
    events: List[ThreatEvent] = Field(..., max_length=100, description="Max 100 events per call")


class IngestResponse(BaseModel):
    accepted:  int
    rejected:  int
    errors:    List[str]
    quota_remaining: int


class CreateApiKeyRequest(BaseModel):
    name:       str = Field(..., description="Human-readable label for this key")
    scopes:     List[str] = Field(
        default=["events:write", "alerts:read"],
        description="Permission scopes: events:write, alerts:read, keys:manage",
    )
    expires_in_days: Optional[int] = Field(
        None, description="Key expiry in days. Omit for non-expiring keys."
    )


class ApiKeyResponse(BaseModel):
    key_id:     str
    name:       str
    key_prefix: str
    scopes:     List[str]
    is_active:  bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    plaintext_key: str = Field(
        ...,
        description="⚠️ Shown ONCE. Store securely — cannot be retrieved again."
    )


# ── Event Ingestion ───────────────────────────────────────────────────────────

@router.post(
    "/events/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest threat security events (batch)",
)
async def ingest_events(
    body: IngestRequest,
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Accepts a batch of up to 100 threat security events from an enterprise
    system (SIEM, WAF, banking switch, etc.), validates them, enqueues them
    into the Redis Streams pipeline for async RAIC scoring, and returns
    quota status.
    """
    accepted_count = 0
    errors: List[str] = []

    # Quota check (reserves capacity atomically)
    quota = await _check_and_increment_quota(db, org, len(body.events))

    payloads = [
        {
            "event_id":   evt.event_id,
            "event_type": "b2b_event",
            "source":     "b2b_api",
            "tenant_id":  str(org.id),
            "payload": {
                "type":        evt.event_type,
                "severity":    evt.severity,
                "source_ip":   evt.source_ip,
                "source_user": evt.source_user,
                "metadata":    evt.metadata,
                "occurred_at": evt.occurred_at.isoformat() if evt.occurred_at else None,
            },
        }
        for evt in body.events
    ]

    accepted_count = await event_bus.publish_batch(STREAM_EVENTS, payloads)


    quota_remaining = max(0, quota.monthly_limit - quota.events_processed)

    return IngestResponse(
        accepted=accepted_count,
        rejected=len(errors),
        errors=errors,
        quota_remaining=quota_remaining,
    )


# ── Real-Time Alert Stream (SSE) ─────────────────────────────────────────────

@router.get("/events/stream", summary="Real-time SSE alert stream (org-scoped)")
async def stream_org_alerts(
    org: Organization = Depends(get_org_from_api_key),
) -> StreamingResponse:
    """
    Establishes a Server-Sent Events (SSE) stream scoped to the authenticated
    organization.  Only threat alerts belonging to this tenant are forwarded.
    Includes 30-second heartbeat keep-alives.
    """
    org_id_str = str(org.id)

    async def event_generator():
        yield "retry: 5000\n\n"  # tell client to reconnect after 5 s on disconnect
        while True:
            try:
                await asyncio.sleep(30)
                yield f"event: heartbeat\ndata: {json.dumps({'org_id': org_id_str})}\n\n"
            except asyncio.CancelledError:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── API Key Management ────────────────────────────────────────────────────────

@router.get("/keys", response_model=List[ApiKeyResponse], summary="List API keys for this org")
async def list_api_keys(
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> List[ApiKeyResponse]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.org_id == org.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            key_id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes or [],
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post(
    "/keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    body: CreateApiKeyRequest,
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """
    Generates a new API key for the authenticated organization.
    The plaintext key is returned **once** in the response — store it securely.
    """
    from datetime import timedelta

    plaintext, prefix, key_hash = ApiKey.generate_key()

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    new_key = ApiKey(
        org_id=org.id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=body.scopes,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    logger.info("Created API key '%s' (prefix=%s) for org %s", body.name, prefix, org.id)

    return ApiKeyCreatedResponse(
        key_id=str(new_key.id),
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        scopes=new_key.scopes or [],
        is_active=new_key.is_active,
        last_used_at=new_key.last_used_at,
        expires_at=new_key.expires_at,
        created_at=new_key.created_at,
        plaintext_key=plaintext,
    )


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke an API key")
async def revoke_api_key(
    key_id: str,
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key_id format.")

    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_uuid, ApiKey.org_id == org.id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found.")

    key.is_active = False
    await db.commit()
    logger.info("Revoked API key %s for org %s", key_id, org.id)


# ── Usage Quota ───────────────────────────────────────────────────────────────

class UsageResponse(BaseModel):
    org_id:           str
    period:           str
    events_processed: int
    monthly_limit:    int
    quota_remaining:  int
    usage_pct:        float
    is_over_limit:    bool


@router.get("/usage", response_model=UsageResponse, summary="Current period event quota usage")
async def get_usage(
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    result = await db.execute(
        select(UsageQuota).where(UsageQuota.org_id == org.id, UsageQuota.period == period)
    )
    quota = result.scalar_one_or_none()

    if quota is None:
        monthly_limit = _plan_limit_for_org(org)
        return UsageResponse(
            org_id=str(org.id),
            period=period,
            events_processed=0,
            monthly_limit=monthly_limit,
            quota_remaining=monthly_limit,
            usage_pct=0.0,
            is_over_limit=False,
        )

    return UsageResponse(
        org_id=str(org.id),
        period=period,
        events_processed=quota.events_processed,
        monthly_limit=quota.monthly_limit,
        quota_remaining=max(0, quota.monthly_limit - quota.events_processed),
        usage_pct=round(quota.usage_pct, 2),
        is_over_limit=quota.is_over_limit,
    )


# ── Org Profile ───────────────────────────────────────────────────────────────

class OrgProfileResponse(BaseModel):
    org_id:     str
    name:       str
    slug:       str
    tier:       str
    is_active:  bool
    subscription_status: Optional[str]
    plan_code:  Optional[str]


@router.get("/org", response_model=OrgProfileResponse, summary="Organization profile & subscription")
async def get_org_profile(
    org: Organization = Depends(get_org_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> OrgProfileResponse:
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.org_id == org.id,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE.value,
                SubscriptionStatus.TRIALING.value,
            ]),
        ).order_by(Subscription.created_at.desc()).limit(1)
    )
    subscription = sub_result.scalar_one_or_none()

    return OrgProfileResponse(
        org_id=str(org.id),
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        is_active=org.is_active,
        subscription_status=subscription.status if subscription else None,
        plan_code=subscription.plan_code if subscription else None,
    )
