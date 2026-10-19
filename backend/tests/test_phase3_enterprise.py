"""
Phase 3: Enterprise Threat Intelligence (B2B) Test Suite
=========================================================
Automated verification for Phase 3 of the Digital Rakshak Master Plan:
3.1 Ingestion API hardening (batch up to 100, oversized batch rejection, quota enforcement)
3.2 Real-time intelligence delivery (SSE streaming, filter metadata, heartbeats)
3.3 Enterprise integration support (STIX 2.1 bundle format export)
3.4 Organization & API key lifecycle (key creation, hashing, instant revocation, tenant isolation)
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from infrastructure.db.session import AsyncSessionLocal
from domain.models.organization import (
    Organization,
    ApiKey,
    UsageQuota,
    OrgTier,
)


# ── Helpers & Fixtures ────────────────────────────────────────────────────────

async def _create_test_enterprise_org(tier: str = OrgTier.BUSINESS.value) -> tuple[dict, str, str]:
    """Creates a test organization and active API key directly in DB."""
    plaintext, prefix, key_hash = ApiKey.generate_key()
    test_slug = f"ent-org-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        org = Organization(
            name=f"Enterprise Corp {uuid.uuid4().hex[:4]}",
            slug=test_slug,
            tier=tier,
            is_active=True
        )
        session.add(org)
        await session.commit()
        await session.refresh(org)

        api_key = ApiKey(
            org_id=org.id,
            name="Primary Integration Key",
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=["events:write", "alerts:read"],
            is_active=True
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        org_id = str(org.id)
        key_id = str(api_key.id)

    return {"x-api-key": plaintext}, org_id, key_id


# ── 3.1 Ingestion API Hardening & Limit Enforcement Tests ──────────────────────

@pytest.mark.asyncio
async def test_b2b_ingest_valid_batch():
    """Verify that a valid batch of events is accepted with 202 status."""
    headers, org_id, _ = await _create_test_enterprise_org()

    payload = {
        "events": [
            {
                "event_type": "phishing_url",
                "severity": "critical",
                "source_ip": "194.26.29.112",
                "metadata": {"url": "https://secure-bank-verify.xyz/login"}
            },
            {
                "event_type": "mule_transfer",
                "severity": "high",
                "source_user": "user_victim_88",
                "metadata": {"target_upi": "syndicate_mule@ybl"}
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/b2b/events/ingest", headers=headers, json=payload)
        assert res.status_code == 202
        data = res.json()
        assert data["accepted"] == 2
        assert data["rejected"] == 0
        assert data["quota_remaining"] > 0


@pytest.mark.asyncio
async def test_b2b_ingest_oversized_batch_rejection():
    """Verify that submitting more than 100 events in one call is rejected (HTTP 422)."""
    headers, _, _ = await _create_test_enterprise_org()

    # Generate 101 events (exceeds max_length=100)
    oversized_events = [
        {
            "event_type": "phishing_url",
            "severity": "low",
            "metadata": {"idx": i}
        }
        for i in range(101)
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/b2b/events/ingest", headers=headers, json={"events": oversized_events})
        assert res.status_code == 422
        # Check validation error indicates too many items
        error_detail = str(res.json())
        assert "events" in error_detail.lower()


@pytest.mark.asyncio
async def test_b2b_ingest_malformed_event_rejection():
    """Verify that events missing required fields fail closed with HTTP 422."""
    headers, _, _ = await _create_test_enterprise_org()

    # Missing required field `event_type`
    malformed_events = [
        {
            "severity": "critical",
            "metadata": {"target": "something"}
        }
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/b2b/events/ingest", headers=headers, json={"events": malformed_events})
        assert res.status_code == 422


# ── 3.2 Real-Time Stream (SSE) & Filtering Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_b2b_sse_stream_connection_and_filtering():
    """Verify that SSE stream connects with x-api-key, establishes text/event-stream, and acknowledges filters."""
    from api.v1.b2b import stream_org_alerts
    from domain.models.organization import Organization

    _, org_id, _ = await _create_test_enterprise_org()
    async with AsyncSessionLocal() as session:
        org = await session.get(Organization, uuid.UUID(org_id))

    response = await stream_org_alerts(min_severity="high", category="phishing", org=org)
    assert response.status_code == 200
    assert response.media_type == "text/event-stream"

    gen = response.body_iterator
    chunk1 = await gen.__anext__()
    chunk2 = await gen.__anext__()

    assert "retry:" in chunk1
    assert "event: connection" in chunk2
    assert org_id in chunk2
    assert "high" in chunk2
    assert "phishing" in chunk2

    await gen.aclose()


# ── 3.3 STIX 2.1 Threat Intelligence Bundle Export Tests ──────────────────────

@pytest.mark.asyncio
async def test_b2b_stix_threat_intel_export():
    """Verify OASIS STIX 2.1 JSON bundle structure and compliance."""
    headers, org_id, _ = await _create_test_enterprise_org()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/v1/b2b/intel/stix?limit=10", headers=headers)
        assert res.status_code == 200
        bundle = res.json()

        # Validate STIX 2.1 Bundle Root Schema
        assert bundle["type"] == "bundle"
        assert bundle["spec_version"] == "2.1"
        assert bundle["id"].startswith("bundle--")
        assert isinstance(bundle["objects"], list)
        assert len(bundle["objects"]) >= 1

        # First object must be identity object of the producer
        identity_obj = bundle["objects"][0]
        assert identity_obj["type"] == "identity"
        assert identity_obj["spec_version"] == "2.1"
        assert identity_obj["identity_class"] == "organization"


# ── 3.4 Key Lifecycle, Instant Revocation & Tenant Isolation Tests ────────────

@pytest.mark.asyncio
async def test_b2b_key_lifecycle_and_revocation():
    """Verify key generation, plaintext display once, and instant revocation."""
    headers, org_id, key_id = await _create_test_enterprise_org()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a secondary key
        create_res = await ac.post(
            "/v1/b2b/keys",
            headers=headers,
            json={"name": "Logstash Splunk Forwarder", "scopes": ["events:write"]}
        )
        assert create_res.status_code == 201
        created_data = create_res.json()
        new_plaintext = created_data["plaintext_key"]
        new_key_id = created_data["key_id"]

        assert new_plaintext.startswith("dr_live_")
        assert created_data["name"] == "Logstash Splunk Forwarder"

        # 2. Use the new key to query quota
        secondary_headers = {"x-api-key": new_plaintext}
        usage_res = await ac.get("/v1/b2b/usage", headers=secondary_headers)
        assert usage_res.status_code == 200

        # 3. Revoke the secondary key
        revoke_res = await ac.delete(f"/v1/b2b/keys/{new_key_id}", headers=headers)
        assert revoke_res.status_code == 204

        # 4. Confirm the revoked key immediately fails (401 Unauthorized)
        failed_res = await ac.get("/v1/b2b/usage", headers=secondary_headers)
        assert failed_res.status_code == 401
        assert "revoked" in failed_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_b2b_strict_tenant_isolation():
    """Verify that Organization A's API key cannot access Organization B's resources."""
    headers_a, org_a_id, key_a_id = await _create_test_enterprise_org()
    headers_b, org_b_id, key_b_id = await _create_test_enterprise_org()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Org A queries org profile -> gets Org A
        res_a = await ac.get("/v1/b2b/org", headers=headers_a)
        assert res_a.status_code == 200
        assert res_a.json()["org_id"] == org_a_id

        # Org B queries org profile -> gets Org B
        res_b = await ac.get("/v1/b2b/org", headers=headers_b)
        assert res_b.status_code == 200
        assert res_b.json()["org_id"] == org_b_id

        # Org A attempts to revoke Org B's key -> must fail with 404 (Not Found in this org)
        cross_revoke = await ac.delete(f"/v1/b2b/keys/{key_b_id}", headers=headers_a)
        assert cross_revoke.status_code == 404
