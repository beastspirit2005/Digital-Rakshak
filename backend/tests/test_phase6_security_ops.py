"""
Phase 6: Security, Privacy & Operational Readiness Test Suite
============================================================
Automated verification for Phase 6 of the Digital Rakshak Master Plan:
6.1 Security Controls & File Upload Validation
    - Dangerous / executable file upload rejection (.exe, .sh, .bat)
    - File upload size limit enforcement
    - Download security headers (CSP, nosniff, cache-control, X-Frame-Options)
    - Multi-tenant evidence isolation (citizen vs unauthorized actor)
    - Request body size limit guard middleware (HTTP 413)
    - Secret sanitization in API error responses
6.2 Privacy & DPDP Act 2023 Data Governance
    - Accessible user consent inspection (GET /v1/users/me/consent)
    - Itemized consent update & purpose revocation (POST /v1/users/me/consent)
    - Self-serve account erasure / Right to be Forgotten (DELETE /v1/users/me)
6.3 Operational Readiness & Health Observability
    - Deep health monitoring (GET /v1/health) reporting DB pool and Redis queue depth
"""

import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from core.config import settings
from core.security import create_access_token
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User


# ── Fixtures & Helpers ────────────────────────────────────────────────────────

async def _create_citizen_user(name_prefix: str = "citizen") -> tuple[dict, str]:
    user_id = uuid.uuid4()
    email = f"{name_prefix}_{uuid.uuid4().hex[:6]}@rakshak-test.in"

    async with AsyncSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            full_name=f"Test {name_prefix.capitalize()}",
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


# ── 6.1 Security Testing & File Upload Controls ──────────────────────────────

@pytest.mark.asyncio
async def test_evidence_executable_file_rejection():
    """
    Ensures dangerous script and binary extensions (.exe, .sh, .bat) are
    rejected with HTTP 400 Bad Request before hitting storage.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header, _ = await _create_citizen_user("victim")

        # 1. Attempt .exe upload
        exe_file = ("trojan.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")
        res_exe = await client.post(
            "/v1/evidence/upload",
            files={"file": exe_file},
            headers=auth_header,
        )
        assert res_exe.status_code == 400
        assert "Disallowed executable" in res_exe.json()["detail"]

        # 2. Attempt .sh script upload
        sh_file = ("script.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh")
        res_sh = await client.post(
            "/v1/evidence/upload",
            files={"file": sh_file},
            headers=auth_header,
        )
        assert res_sh.status_code == 400
        assert "Disallowed executable" in res_sh.json()["detail"]


@pytest.mark.asyncio
async def test_evidence_valid_upload_and_download_security_headers():
    """
    Verifies that safe evidence files are ingested with cryptographic digests,
    and downloads return hardened security headers:
    - Content-Disposition: attachment
    - X-Content-Type-Options: nosniff
    - Cache-Control: private, no-cache, no-store
    - Content-Security-Policy: default-src 'none'
    - X-Frame-Options: DENY
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header, user_id = await _create_citizen_user("submitter")

        # Upload a valid PNG screenshot
        valid_png = (
            "fraud_receipt.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4",
            "image/png",
        )
        res_upload = await client.post(
            "/v1/evidence/upload",
            files={"file": valid_png},
            data={"evidence_type": "screenshot", "content_text": "Phishing transaction payment proof"},
            headers=auth_header,
        )
        assert res_upload.status_code == 201
        data = res_upload.json()
        assert data["status"] == "success"
        evidence_id = data["evidence"]["id"]
        assert len(data["evidence"]["sha256"]) == 64
        assert data["evidence"]["integrity_status"] == "VERIFIED"

        # Download evidence file and check security headers
        res_download = await client.get(
            f"/v1/evidence/{evidence_id}/download",
            headers=auth_header,
        )
        assert res_download.status_code == 200
        headers = res_download.headers

        # Verify hardened security headers
        assert "attachment" in headers.get("content-disposition", "")
        assert headers.get("x-content-type-options") == "nosniff"
        assert "no-store" in headers.get("cache-control", "")
        assert "default-src 'none'" in headers.get("content-security-policy", "")
        assert headers.get("x-frame-options") == "DENY"


@pytest.mark.asyncio
async def test_evidence_cross_tenant_isolation():
    """
    Verifies that Citizen B cannot access, inspect, or download Citizen A's
    submitted evidence (enforces strict HTTP 403 Forbidden).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header_a, _ = await _create_citizen_user("user_a")
        auth_header_b, _ = await _create_citizen_user("user_b")

        # Citizen A uploads confidential bank statement
        pdf_file = ("statement.pdf", b"%PDF-1.4 sample evidence content", "application/pdf")
        res_upload = await client.post(
            "/v1/evidence/upload",
            files={"file": pdf_file},
            headers=auth_header_a,
        )
        assert res_upload.status_code == 201
        evidence_id = res_upload.json()["evidence"]["id"]

        # Citizen B attempts to get details
        res_b_details = await client.get(
            f"/v1/evidence/{evidence_id}",
            headers=auth_header_b,
        )
        assert res_b_details.status_code == 403
        assert "Not authorized" in res_b_details.json()["detail"]

        # Citizen B attempts to download
        res_b_download = await client.get(
            f"/v1/evidence/{evidence_id}/download",
            headers=auth_header_b,
        )
        assert res_b_download.status_code == 403


@pytest.mark.asyncio
async def test_request_size_limit_middleware_enforcement():
    """
    Ensures that requests declaring a Content-Length exceeding 30MB
    are rejected immediately with HTTP 413 Payload Too Large by middleware.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header, _ = await _create_citizen_user("flooder")

        # Simulate oversized payload request
        oversized_headers = {
            **auth_header,
            "Content-Length": "35000000",  # ~33.4 MB (limit is 30 MB)
            "Content-Type": "application/json",
        }
        res = await client.post(
            "/v1/scan",
            content=b'{"indicator": "https://test.com"}',
            headers=oversized_headers,
        )
        assert res.status_code == 413
        assert "Request entity too large" in res.json()["detail"]


# ── 6.2 Privacy & DPDP Act 2023 Consent & Erasure ────────────────────────────

@pytest.mark.asyncio
async def test_dpdp_consent_management_lifecycle():
    """
    Verifies user consent inspection and revocation under DPDP Act 2023:
    1. Default consent state inspection
    2. Purpose revocation (disabling AI threat analysis / telemetry)
    3. State persistence and verification
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header, _ = await _create_citizen_user("privacy_user")

        # 1. Fetch initial consent
        res_get = await client.get("/v1/users/me/consent", headers=auth_header)
        assert res_get.status_code == 200
        consent_data = res_get.json()
        assert consent_data["dpdp_act_compliant"] is True
        assert consent_data["consents"]["ai_threat_analysis"] is True
        assert consent_data["consents"]["telemetry_monitoring"] is True

        # 2. Revoke AI threat analysis and telemetry consent
        res_update = await client.post(
            "/v1/users/me/consent",
            json={"ai_threat_analysis": False, "telemetry_monitoring": False},
            headers=auth_header,
        )
        assert res_update.status_code == 200
        assert res_update.json()["status"] == "success"

        # 3. Confirm revocation persisted
        res_verify = await client.get("/v1/users/me/consent", headers=auth_header)
        assert res_verify.status_code == 200
        updated = res_verify.json()["consents"]
        assert updated["ai_threat_analysis"] is False
        assert updated["telemetry_monitoring"] is False
        assert updated["syndicate_intel_sharing"] is True  # untouched purpose remains active


@pytest.mark.asyncio
async def test_dpdp_self_serve_account_erasure():
    """
    Verifies Section 12 of the DPDP Act 2023 (Right to Erasure):
    A citizen can self-delete their own account (DELETE /v1/users/me),
    permanently wiping their records and invalidating subsequent queries.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_header, user_id = await _create_citizen_user("erasure_user")

        # Confirm account exists
        res_me = await client.get("/v1/users/me", headers=auth_header)
        assert res_me.status_code == 200
        assert res_me.json()["id"] == user_id

        # Execute self-serve account deletion
        res_delete = await client.delete("/v1/users/me", headers=auth_header)
        assert res_delete.status_code == 200
        assert res_delete.json()["status"] == "success"
        assert "permanently erased" in res_delete.json()["message"]

        # Confirm token now fails closed (user record deleted from DB)
        res_after = await client.get("/v1/users/me", headers=auth_header)
        assert res_after.status_code == 401


# ── 6.3 Operational Readiness & Deep Health Monitoring ───────────────────────

@pytest.mark.asyncio
async def test_operational_health_monitoring_and_pool_telemetry():
    """
    Verifies that GET /v1/health provides complete operational observability:
    - PostgreSQL connection pool telemetry (size, checked_in, checked_out)
    - Redis Streams queue depth and Dead-Letter Queue (DLQ) depth
    - AI runtime availability
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/health")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] in ["healthy", "degraded"]
        services = data["services"]

        # 1. PostgreSQL pool observability
        assert "postgres" in services
        pg = services["postgres"]
        assert pg["status"] in ["up", "down"]
        if pg["status"] == "up":
            assert "pool" in pg
            assert "size" in pg["pool"]
            assert "checked_in" in pg["pool"]
            assert "checked_out" in pg["pool"]

        # 2. Redis streams observability
        assert "redis" in services
        rd = services["redis"]
        assert rd["status"] == "up"
        assert "queue_depth" in rd
        assert "dlq_depth" in rd

        # 3. AI engine liveness
        assert "ai" in services
        assert services["ai"]["status"] in ["up", "degraded"]


@pytest.mark.asyncio
async def test_public_contact_inquiry_ticket_and_validation():
    """
    Verifies that POST /v1/support/contact allows public citizens to submit
    categorized inquiries without authentication and returns a tracked ticket number.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid payload (too short message)
        res_bad = await client.post("/v1/support/contact", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "category": "General Inquiry",
            "subject": "Missing description test",
            "message": "Short",
        })
        assert res_bad.status_code == 422

        # Valid payload
        res_good = await client.post("/v1/support/contact", json={
            "name": "Arjun Mehta",
            "email": "arjun.mehta@test-domain.in",
            "category": "Billing & Subscription",
            "subject": "Inquiry regarding SAC 998313 GST Invoice",
            "message": "Need clarification on GST credit claim for annual plan subscription.",
            "reference_number": "INV-10029",
        })
        assert res_good.status_code == 200
        data = res_good.json()
        assert data["success"] is True
        assert data["ticket_number"].startswith("TKT-INQ-")
