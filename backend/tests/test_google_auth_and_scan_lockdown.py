"""
Automated Test Battery: Google Zero Auth & Scanner Access Lockdown
===================================================================
Verifies:
1. All scanner endpoints strictly reject unauthenticated/guest calls with HTTP 401.
2. Authenticated free citizens can scan URLs/text/UPI for free (Personal Pro Shield free tier).
3. APK scanning requires Pro tier (HTTP 402 Payment Required for free citizens).
4. Google Zero Auth (Sign in with Google) auto-provisions verified citizen accounts.
5. Google Zero Auth strictly blocks official institutional roles (Police, Cyber Cell, Bank Officers).
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from core.security import create_access_token


@pytest.mark.asyncio
async def test_unauthenticated_scan_returns_401():
    """Verify that unauthenticated callers cannot scan any indicator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. URL / Text / UPI scan
        res = await client.post("/v1/scan", json={"url": "https://malicious-test-link.com"})
        assert res.status_code == 401

        # 2. QR scan
        res_qr = await client.post("/v1/scan/qr")
        assert res_qr.status_code == 401

        # 3. APK scan
        res_apk = await client.post("/v1/scan/apk")
        assert res_apk.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_citizen_free_scan_returns_200():
    """Verify that an authenticated citizen can use Personal Pro Shield scanning for free."""
    uid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user = User(
            id=uid,
            email=f"citizen_free_{uid.hex[:6]}@example.com",
            role="citizen",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",
            b2c_subscription_status="active",
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": str(uid), "email": user.email, "role": "citizen"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/scan",
            json={"url": "https://yono-sbi-update.in/kyc"},
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_safe"] is False
        assert data["risk_level"] == "CRITICAL"
        # Free citizen should not have Attack DNA
        assert data.get("attack_dna_match") is None


@pytest.mark.asyncio
async def test_free_citizen_apk_scan_requires_pro():
    """Verify that APK decompilation returns 402 Payment Required for free citizens."""
    uid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user = User(
            id=uid,
            email=f"free_user_{uid.hex[:6]}@example.com",
            role="citizen",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",
            b2c_subscription_status="active",
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": str(uid), "email": user.email, "role": "citizen"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call APK scan with dummy file
        files = {"file": ("test.apk", b"PK\x03\x04dummyapkcontent", "application/vnd.android.package-archive")}
        res = await client.post("/v1/scan/apk", files=files, headers=headers)
        assert res.status_code == 402
        assert "Pro subscription required" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_pro_subscriber_apk_scan_passes_pro_gate():
    """Verify that a Pro subscriber bypasses the 402 Payment Required check on APK scan."""
    uid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user = User(
            id=uid,
            email=f"pro_user_{uid.hex[:6]}@example.com",
            role="citizen",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_pro_annual",
            b2c_subscription_status="active",
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": str(uid), "email": user.email, "role": "citizen"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call APK scan with dummy file - it should NOT return 402
        files = {"file": ("test.apk", b"PK\x03\x04dummyapkcontent", "application/vnd.android.package-archive")}
        res = await client.post("/v1/scan/apk", files=files, headers=headers)
        # Should not be 402; may be 400 or 500 because it's dummy bytes, but Pro gate was cleared!
        assert res.status_code != 402


@pytest.mark.asyncio
async def test_google_auth_provisions_new_citizen():
    """Verify that Google Zero Auth automatically registers a verified Citizen."""
    random_hex = uuid.uuid4().hex[:6]
    mock_email = f"new_google_citizen_{random_hex}@gmail.com"
    mock_name = f"Google Citizen {random_hex}"
    mock_token = f"mock_google_token_{mock_email}|{mock_name}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/v1/auth/google", json={"credential": mock_token})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == mock_email
        assert data["user"]["role"] == "citizen"
        assert data["user"]["full_name"] == mock_name


@pytest.mark.asyncio
async def test_google_auth_blocks_official_roles():
    """Verify that institutional official roles (Police, Banker, Admin) cannot sign in via Google."""
    uid = uuid.uuid4()
    police_email = f"investigator_{uid.hex[:6]}@police.gov.in"
    async with AsyncSessionLocal() as session:
        user = User(
            id=uid,
            email=police_email,
            role="police",
            is_active=True,
            is_approved=True,
        )
        session.add(user)
        await session.commit()

    mock_token = f"mock_google_token_{police_email}|Officer Sharma"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/v1/auth/google", json={"credential": mock_token})
        assert res.status_code == 403
        detail = res.json().get("detail", "")
        assert "Institutional personnel" in detail
        assert "departmental credentials" in detail
