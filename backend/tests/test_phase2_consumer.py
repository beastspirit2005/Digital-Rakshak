"""
Phase 2: Consumer MVP — Digital Rakshak Personal Test Suite
============================================================
Automated verification for Phase 2 of the Digital Rakshak Master Plan:
2.1 Multi-Vector Indicator Scanner (URL, SMS/text, UPI, Phone, QR)
2.2 4-Tier Indicator Classification Taxonomy (KNOWN_MALICIOUS, SUSPICIOUS, UNKNOWN_UNVERIFIED, VERIFIED_LEGITIMATE)
2.3 Actionable Consumer Safety Guidance
2.4 User-Specific Scan History Persistence and Deletion (Isolated per Account)
2.5 Free vs Pro Feature Gating (Attack DNA & Graph Correlation)
2.6 Sub-5ms Indicator Cache Consistency
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from domain.models.user import User
from core.security import create_access_token
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.db.session import AsyncSessionLocal


# ── Fixtures & Helpers ────────────────────────────────────────────────────────

async def _create_test_user(role: str = "citizen", is_pro: bool = False) -> tuple[dict, str]:
    user_id = uuid.uuid4()
    email = f"citizen_{uuid.uuid4().hex[:6]}@example.com"
    plan_code = "b2c_pro_149" if is_pro else "b2c_free"
    sub_status = "active" if is_pro else "inactive"

    async with AsyncSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            role=role,
            is_active=True,
            is_approved=True,
            b2c_plan_code=plan_code,
            b2c_subscription_status=sub_status,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({
        "sub": str(user_id),
        "email": email,
        "role": role,
    })
    return {"Authorization": f"Bearer {token}"}, str(user_id)


# ── 2.1 Multi-Vector OSINT & Indicator Classification Tests ───────────────────

def test_osint_multi_vector_classification():
    """Verify 4-tier indicator classification across URL, Phone, UPI, and Text."""
    scanner = OSINTScanner()

    # 1. Known Malicious Domain
    bad_url_res = scanner.scan_text("https://yono-sbi-update.in/kyc")
    assert bad_url_res["risk_level"] == "CRITICAL"
    assert bad_url_res["indicator_status"] == "KNOWN_MALICIOUS"
    assert any("yono-sbi-update.in" in f["threat"] for f in bad_url_res["flagged_urls"])

    # 2. Verified Legitimate Banking Domain
    good_url_res = scanner.scan_text("https://retail.onlinesbi.sbi/retail/login.htm")
    assert good_url_res["indicator_status"] == "VERIFIED_LEGITIMATE"
    assert good_url_res["risk_level"] == "LOW"

    # 3. Known Malicious UPI Handle
    bad_upi_res = scanner.scan_upi("axis-care-refund@okaxis")
    assert bad_upi_res["flagged"] is True
    assert bad_upi_res["risk_level"] == "CRITICAL"
    assert bad_upi_res["indicator_status"] == "KNOWN_MALICIOUS"

    # 4. Verified Legitimate UPI Identifier
    good_upi_res = scanner.scan_upi("merchant_nodal@npci")
    assert good_upi_res["indicator_status"] == "VERIFIED_LEGITIMATE"
    assert good_upi_res["flagged"] is False

    # 5. Unknown / Unverified UPI Handle (Neutral Caution)
    unknown_upi_res = scanner.scan_upi("rahul.sharma@okaxis")
    assert unknown_upi_res["flagged"] is False
    assert unknown_upi_res["indicator_status"] == "UNKNOWN_UNVERIFIED"

    # 6. Official National Cyber Helpline
    good_phone_res = scanner.scan_phone("1930")
    assert good_phone_res["indicator_status"] == "VERIFIED_LEGITIMATE"
    assert good_phone_res["risk_level"] == "LOW"

    # 7. High-Risk Foreign WhatsApp Vishing Prefix
    bad_phone_res = scanner.scan_phone("+923001234567")
    assert bad_phone_res["flagged"] is True
    assert bad_phone_res["risk_level"] == "CRITICAL"
    assert bad_phone_res["indicator_status"] == "SUSPICIOUS"

    # 8. Counterfeit Authority Impersonation Text (Digital Arrest)
    arrest_text_res = scanner.scan_text("CBI officer demanding immediate video call interrogation")
    assert arrest_text_res["risk_level"] == "HIGH"
    assert arrest_text_res["indicator_status"] == "SUSPICIOUS"
    assert len(arrest_text_res["counterfeit_warnings"]) > 0


# ── 2.2 Live Scan API Multi-Vector & Guidance Verification ───────────────────

@pytest.mark.asyncio
async def test_live_scan_api_guest_and_guidance():
    """Verify that unauthenticated guests can scan and receive 4-tier status + guidance."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Scan malicious domain as guest
        res = await ac.post("/v1/scan", json={"url": "https://update-pan-kyc.com/login"})
        assert res.status_code == 200
        data = res.json()

        assert data["is_safe"] is False
        assert data["risk_level"] == "CRITICAL"
        assert data["indicator_status"] == "KNOWN_MALICIOUS"
        assert len(data["reasons"]) > 0
        assert len(data["guidance"]) > 0
        assert any("domain name" in g.lower() for g in data["guidance"])
        # Guests should NOT receive Pro enrichment
        assert data.get("attack_dna_match") is None
        assert data.get("related_cases") is None


@pytest.mark.asyncio
async def test_live_scan_phone_vector():
    """Verify phone vector scanning through the API."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Scan official emergency helpline
        res_helpline = await ac.post("/v1/scan", json={"phone": "1930"})
        assert res_helpline.status_code == 200
        data_helpline = res_helpline.json()
        assert data_helpline["is_safe"] is True
        assert data_helpline["indicator_status"] == "VERIFIED_LEGITIMATE"

        # Scan high-risk foreign vishing caller
        res_vishing = await ac.post("/v1/scan", json={"phone": "+923129876543"})
        assert res_vishing.status_code == 200
        data_vishing = res_vishing.json()
        assert data_vishing["is_safe"] is False
        assert data_vishing["indicator_status"] == "SUSPICIOUS"
        assert any("1930" in g for g in data_vishing["guidance"])


@pytest.mark.asyncio
async def test_free_vs_pro_tier_entitlement():
    """Verify that Pro users receive Attack DNA & Graph correlation while Free users receive basic results."""
    free_headers, _ = await _create_test_user(role="citizen", is_pro=False)
    pro_headers, _ = await _create_test_user(role="citizen", is_pro=True)

    test_payload = {"upi": "fake_lottery_desk@icici"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Free User Scan
        res_free = await ac.post("/v1/scan", json=test_payload, headers=free_headers)
        assert res_free.status_code == 200
        data_free = res_free.json()
        assert data_free["is_safe"] is False
        assert data_free.get("attack_dna_match") is None
        assert data_free.get("related_cases") is None

        # Pro User Scan
        res_pro = await ac.post("/v1/scan", json=test_payload, headers=pro_headers)
        assert res_pro.status_code == 200
        data_pro = res_pro.json()
        assert data_pro["is_safe"] is False
        assert data_pro.get("attack_dna_match") is not None
        assert data_pro.get("related_cases") is not None


# ── 2.3 User Scan History Persistence & Isolation Tests ───────────────────────

@pytest.mark.asyncio
async def test_scan_history_lifecycle_and_tenant_isolation():
    """Verify that scan history is isolated per account, retrievable, and clearable."""
    user_a_headers, user_a_id = await _create_test_user(role="citizen")
    user_b_headers, user_b_id = await _create_test_user(role="citizen")

    unique_scan_a = f"https://custom-test-{uuid.uuid4().hex[:6]}.com"
    unique_scan_b = f"https://custom-test-{uuid.uuid4().hex[:6]}.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User A executes a scan
        res_a = await ac.post("/v1/scan", json={"url": unique_scan_a}, headers=user_a_headers)
        assert res_a.status_code == 200

        # User B executes a scan
        res_b = await ac.post("/v1/scan", json={"url": unique_scan_b}, headers=user_b_headers)
        assert res_b.status_code == 200

        # User A fetches scan history -> must only see User A's scans
        history_a = await ac.get("/v1/scan/history", headers=user_a_headers)
        assert history_a.status_code == 200
        items_a = history_a.json()
        assert any(item.get("input") == unique_scan_a for item in items_a)
        assert not any(item.get("input") == unique_scan_b for item in items_a)

        # User B fetches scan history -> must only see User B's scans
        history_b = await ac.get("/v1/scan/history", headers=user_b_headers)
        assert history_b.status_code == 200
        items_b = history_b.json()
        assert any(item.get("input") == unique_scan_b for item in items_b)
        assert not any(item.get("input") == unique_scan_a for item in items_b)

        # User A clears history
        del_res = await ac.delete("/v1/scan/history", headers=user_a_headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "ok"

        # User A history is now empty
        empty_a = await ac.get("/v1/scan/history", headers=user_a_headers)
        assert empty_a.status_code == 200
        assert len(empty_a.json()) == 0

        # User B history remains intact (cross-user isolation maintained)
        intact_b = await ac.get("/v1/scan/history", headers=user_b_headers)
        assert intact_b.status_code == 200
        assert any(item.get("input") == unique_scan_b for item in intact_b.json())
