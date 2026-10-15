"""
Comprehensive Role-Based Access Control (RBAC) & User-Specific Scans Test Suite
================================================================================
Verifies:
1. Official / Institutional roles (Police, Cyber Cell, Bank Officers, Admin) have
   automatic complimentary full-tier access without consumer subscription fees.
2. Consumer Citizens (citizen) require a valid Pro subscription for Pro features.
3. Billing endpoints properly return institutional status for officials and reject
   unneeded B2C subscription attempts for them.
4. B2B multi-tenant isolation blocks unauthorized users from defaulting to other orgs.
5. Prevention scan Attack DNA is unlocked for official roles.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from core.security import create_access_token
from api.deps import require_pro_user, OFFICIAL_INSTITUTIONAL_ROLES


@pytest.mark.asyncio
async def test_official_roles_are_exempt_from_b2c_subscription():
    """Police, Cyber Cell, Bankers, and Admins must never receive HTTP 402."""
    for role in ["police", "cyber_cell", "banker", "bank_employee", "admin"]:
        user = User(
            id=uuid.uuid4(),
            email=f"test_{role}_{uuid.uuid4().hex[:6]}@rakshak.gov.in",
            role=role,
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",  # free consumer plan, but official role!
            b2c_subscription_status="active",
        )
        result_user = await require_pro_user(user)
        assert result_user.id == user.id
        assert result_user.role == role


@pytest.mark.asyncio
async def test_citizen_on_free_tier_is_blocked_by_pro_guard():
    """Citizens on free tier MUST receive HTTP 402 Payment Required."""
    citizen = User(
        id=uuid.uuid4(),
        email=f"citizen_{uuid.uuid4().hex[:6]}@gmail.com",
        role="citizen",
        is_active=True,
        is_approved=True,
        b2c_plan_code="b2c_free",
        b2c_subscription_status="active",
    )
    with pytest.raises(Exception) as excinfo:
        await require_pro_user(citizen)
    assert excinfo.value.status_code == 402
    assert "subscription required" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_citizen_with_active_pro_is_allowed():
    """Citizens with active Pro subscription pass the pro guard."""
    pro_citizen = User(
        id=uuid.uuid4(),
        email=f"pro_citizen_{uuid.uuid4().hex[:6]}@gmail.com",
        role="citizen",
        is_active=True,
        is_approved=True,
        b2c_plan_code="b2c_pro_149",
        b2c_subscription_status="active",
    )
    result = await require_pro_user(pro_citizen)
    assert result.id == pro_citizen.id


@pytest.mark.asyncio
async def test_institutional_billing_and_scan_e2e_flow():
    """Tests billing status, subscription rejection, and scan enrichment for an officer."""
    officer_id = uuid.uuid4()
    officer_email = f"officer_{uuid.uuid4().hex[:6]}@police.gov.in"

    citizen_id = uuid.uuid4()
    citizen_email = f"stranger_{uuid.uuid4().hex[:6]}@gmail.com"

    async with AsyncSessionLocal() as session:
        officer = User(
            id=officer_id,
            email=officer_email,
            role="police",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",
        )
        citizen = User(
            id=citizen_id,
            email=citizen_email,
            role="citizen",
            is_active=True,
            is_approved=True,
            b2c_plan_code="b2c_free",
        )
        session.add_all([officer, citizen])
        await session.commit()

    officer_token = create_access_token({"sub": str(officer_id), "email": officer_email, "role": "police"})
    citizen_token = create_access_token({"sub": str(citizen_id), "email": citizen_email, "role": "citizen"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check GET /v1/billing/status returns institutional market for officer
        res_status = await client.get("/v1/billing/status", headers={"Authorization": f"Bearer {officer_token}"})
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["market"] == "institutional"
        assert status_data["is_pro"] is True

        # 2. Check POST /v1/billing/create-subscription rejects officer with 400
        res_sub = await client.post(
            "/v1/billing/create-subscription",
            headers={"Authorization": f"Bearer {officer_token}"},
            json={"plan_code": "b2c_pro_149"}
        )
        assert res_sub.status_code == 400
        assert "institutional" in res_sub.json()["detail"].lower()

        # 3. Check POST /v1/scan unlocks Attack DNA for officer automatically
        res_scan = await client.post(
            "/v1/scan",
            headers={"Authorization": f"Bearer {officer_token}"},
            json={"url": "http://secure-sbi-update.in/kyc-fix"}
        )
        assert res_scan.status_code == 200
        scan_data = res_scan.json()
        assert scan_data.get("attack_dna_match") is not None
        assert scan_data.get("related_cases") is not None

        # 4. Check B2B multi-tenant isolation: citizen without org receives 403 Forbidden
        res_b2b = await client.get("/v1/b2b/keys", headers={"Authorization": f"Bearer {citizen_token}"})
        assert res_b2b.status_code == 403
        assert "not a member" in res_b2b.json()["detail"].lower()
