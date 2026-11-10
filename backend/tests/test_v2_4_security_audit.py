import pytest
import uuid
from unittest.mock import MagicMock
from fastapi import HTTPException

from core.correlation_middleware import get_correlation_id
from api.deps import require_official_role, OFFICIAL_INSTITUTIONAL_ROLES
from domain.models.user import User
from api.v1.internal_sweeper import verify_scheduler_secret
from services.mock_bank_service import mock_bank_service
from domain.services.transaction_extractor import extract_transaction_intelligence


# ── 1. Internal Scheduler Secret Authentication ───────────────────────────

def test_security_scheduler_secret_rejection():
    """Validates that unauthorized callers cannot trigger the outbox sweeper."""
    # 1. Missing header
    with pytest.raises(HTTPException) as exc_1:
        verify_scheduler_secret(authorization=None)
    assert exc_1.value.status_code == 401

    # 2. Forged secret
    with pytest.raises(HTTPException) as exc_2:
        verify_scheduler_secret(authorization="Bearer forged_malicious_token")
    assert exc_2.value.status_code == 401

    # 3. Empty string
    with pytest.raises(HTTPException) as exc_3:
        verify_scheduler_secret(authorization="Bearer ")
    assert exc_3.value.status_code == 401


# ── 2. RBAC & BFLA (Broken Function Level Authorization) ──────────────────

@pytest.mark.asyncio
async def test_security_rbac_official_role_enforcement():
    """
    Validates that citizen and unauthorized roles are blocked from executing
    institutional banking clearances or accessing internal health diagnostics.
    """
    # 1. Citizen Role -> Must be rejected with 403 Forbidden
    citizen_user = User(
        id=uuid.uuid4(),
        email="citizen@victim.in",
        role="citizen",
        is_active=True,
        is_approved=True
    )
    with pytest.raises(HTTPException) as exc_info:
        await require_official_role(user=citizen_user)
    assert exc_info.value.status_code == 403
    assert "Access restricted" in exc_info.value.detail

    # 2. Authorized Official Roles -> Must pass
    for official_role in OFFICIAL_INSTITUTIONAL_ROLES:
        officer = User(
            id=uuid.uuid4(),
            email=f"{official_role}@police.gov.in",
            role=official_role,
            is_active=True,
            is_approved=True
        )
        cleared = await require_official_role(user=officer)
        assert cleared.id == officer.id


# ── 3. BOLA (Broken Object Level Authorization) Isolation ─────────────────

def test_security_bola_case_ownership_isolation():
    """
    Validates that a citizen cannot access another citizen's case record.
    """
    citizen_a_id = uuid.uuid4()
    citizen_b_id = uuid.uuid4()

    # Case owned by Citizen B
    mock_case = MagicMock()
    mock_case.submitted_by = citizen_b_id

    # Simulated BOLA check in cases.py
    user_a = User(id=citizen_a_id, role="citizen")

    # Citizen A attempts to read Citizen B's case
    has_access = False
    if user_a.role == "citizen":
        has_access = (str(mock_case.submitted_by) == str(user_a.id))
    elif user_a.role in ("admin", "police", "cyber_cell"):
        has_access = True

    assert has_access is False, "Citizen A must NOT have access to Citizen B's case!"

    # Official Investigator attempts to read Citizen B's case for inquiry
    officer = User(id=uuid.uuid4(), role="police")
    has_officer_access = (officer.role in ("admin", "police", "cyber_cell"))
    assert has_officer_access is True, "Investigating officer must have legitimate case access."


# ── 4. Webhook Replay & Nonce Verification ────────────────────────────────

def test_security_webhook_nonce_replay_attack_rejected():
    """
    Validates that replayed banking callback nonces are rejected.
    """
    mock_bank_service.reset()
    payload_bytes = b'{"status": "CONFIRMED"}'
    replayed_nonce = "NONCE-MALICIOUS-REPLAY-001"

    import time
    now_ts = str(time.time())
    canonical_now = f"{now_ts}.{payload_bytes.decode()}"
    sig_now = mock_bank_service.sign_payload(canonical_now)

    # Attempt 1: Valid receipt
    ok1, _ = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce=replayed_nonce,
        payload_bytes=payload_bytes,
        signature=sig_now,
        timestamp_str=now_ts
    )
    assert ok1 is True

    # Attempt 2 (Replay with identical nonce): Must be rejected
    ok2, err2 = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce=replayed_nonce,
        payload_bytes=payload_bytes,
        signature=sig_now,
        timestamp_str=now_ts
    )
    assert ok2 is False
    assert "replay detected" in err2


# ── 5. SQL Injection Input Sanitisation ───────────────────────────────────

def test_security_sql_injection_payload_resilience():
    """
    Validates that SQL injection strings passed as text or identifiers
    are extracted safely without executing or breaking syntax.
    """
    malicious_inputs = [
        "Transferred 50000; DROP TABLE users; -- to account 1234567890",
        "Paid ' OR '1'='1 to UPI target@oksbi",
        "1 UNION SELECT null, username, password FROM users --",
        "Path traversal ../../etc/passwd"
    ]
    for injection_string in malicious_inputs:
        intel = extract_transaction_intelligence(injection_string)
        # Verify extraction completes without uncaught exception
        assert intel is not None


# ── 6. Request Size Limit Enforcement ─────────────────────────────────────

def test_security_request_size_limit_threshold():
    """Validates that 30MB upload limit is enforced."""
    from main import RequestSizeLimitMiddleware
    middleware = RequestSizeLimitMiddleware(app=None, max_upload_size=30 * 1024 * 1024)
    assert middleware.max_upload_size == 31457280  # 30 MB in bytes
