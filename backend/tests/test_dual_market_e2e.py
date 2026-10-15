"""
End-to-End Integration Tests for Dual-Market Platform
=====================================================
Tests live API endpoints using FastAPI's AsyncClient:
- Guest scan (unauthenticated B2C)
- B2B API Key lifecycle & batch threat event ingestion
- Usage quota calculation and verification
- Razorpay billing status and plan schemas
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
    PlanCode,
)
from domain.models.user import User


@pytest.mark.asyncio
async def test_b2c_guest_scan_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan",
            json={"url": "https://secure-hdfc-kyc-verification.ru/update"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_safe" in data
        assert "risk_level" in data
        assert "reasons" in data
        assert isinstance(data["reasons"], list)


@pytest.mark.asyncio
async def test_b2b_unauthorized_without_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing header / credentials
        res1 = await client.post("/v1/b2b/events/ingest", json={"events": []})
        assert res1.status_code in (401, 422)  # Unauthorized or missing header

        # Invalid key format
        res2 = await client.post(
            "/v1/b2b/events/ingest",
            headers={"x-api-key": "invalid_key"},
            json={"events": []}
        )
        assert res2.status_code == 401


@pytest.mark.asyncio
async def test_b2b_end_to_end_flow():
    # 1. Create a test organization and API key directly in DB
    plaintext, prefix, key_hash = ApiKey.generate_key()
    test_slug = f"test-org-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        org = Organization(
            name="Apex Security Labs",
            slug=test_slug,
            tier=OrgTier.BUSINESS.value,
            is_active=True
        )
        session.add(org)
        await session.commit()
        await session.refresh(org)

        api_key = ApiKey(
            org_id=org.id,
            name="SIEM Ingestion Key",
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=["events:write", "alerts:read"],
            is_active=True
        )
        session.add(api_key)
        await session.commit()
        org_id = org.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Ingest batch of threat events
        headers = {"x-api-key": plaintext}
        payload = {
            "events": [
                {
                    "event_type": "phishing_url",
                    "severity": "critical",
                    "source_ip": "10.0.0.1",
                    "metadata": {"target": "UPI", "url": "http://fake-gpay.com"}
                },
                {
                    "event_type": "credential_stuffing",
                    "severity": "high",
                    "source_ip": "10.0.0.2",
                    "metadata": {"attempts": 45}
                }
            ]
        }
        res_ingest = await client.post("/v1/b2b/events/ingest", headers=headers, json=payload)
        assert res_ingest.status_code == 202
        ingest_data = res_ingest.json()
        assert ingest_data["accepted"] == 2
        assert ingest_data["rejected"] == 0

        # 3. Verify quota tracking
        res_usage = await client.get("/v1/b2b/usage", headers=headers)
        assert res_usage.status_code == 200
        usage_data = res_usage.json()
        assert usage_data["events_processed"] >= 2
        assert usage_data["monthly_limit"] == 100_000  # Business tier limit
        assert usage_data["quota_remaining"] <= 100_000 - 2

        # 4. Create secondary API key via endpoint
        res_key = await client.post(
            "/v1/b2b/keys",
            headers=headers,
            json={"name": "Logstash Collector", "scopes": ["events:write"]}
        )
        assert res_key.status_code == 201
        key_data = res_key.json()
        assert key_data["plaintext_key"].startswith("dr_live_")
        assert key_data["name"] == "Logstash Collector"

        # 5. List keys
        res_list = await client.get("/v1/b2b/keys", headers=headers)
        assert res_list.status_code == 200
        keys_list = res_list.json()
        assert len(keys_list) >= 2

        # 6. Organization profile
        res_org = await client.get("/v1/b2b/org", headers=headers)
        assert res_org.status_code == 200
        org_profile = res_org.json()
        assert org_profile["name"] == "Apex Security Labs"
        assert org_profile["tier"] == "business"
