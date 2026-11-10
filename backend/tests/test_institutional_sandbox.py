import pytest
import uuid
import time
import json
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from typing import Tuple

from domain.models.bank import BankEscalation, BankRegistry
from domain.services.bank_integrations.sandbox_adapter import SandboxBankAdapter
from services.mock_bank_service import mock_bank_service, SandboxScenario


@pytest.fixture(autouse=True)
def reset_mock_bank():
    """Resets mock bank idempotency store and scenarios before each test."""
    mock_bank_service.reset()
    yield
    mock_bank_service.reset()


def make_dummy_escalation(
    bank_code: str = "SBIN",
    amount: Decimal = Decimal("25000.00"),
    idempotency_key: str = None
) -> Tuple[BankEscalation, BankRegistry]:
    """Helper to construct dummy escalation and target bank records."""
    key = idempotency_key or f"IDEMP-TEST-{uuid.uuid4().hex[:8]}"
    bank = BankRegistry(
        id=uuid.uuid4(),
        bank_code=bank_code,
        bank_name=f"State Bank of India ({bank_code})",
        ifsc_prefix=bank_code[:4],
        integration_type="SANDBOX_API"
    )
    esc = BankEscalation(
        id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        alert_reference=f"DR-ALERT-TEST-{uuid.uuid4().hex[:6]}",
        target_bank_id=bank.id,
        escalation_role="BENEFICIARY_BANK",
        instruction_category="STATUTORY_FREEZE_ORDER",
        statutory_basis="SECTION_106_BNSS",
        idempotency_key=key,
        alert_payload={"test": "payload"}
    )
    return esc, bank


# ── 1. Receiver-Side Idempotency Tests ────────────────────────────────────

def test_sandbox_successful_dispatch_and_receiver_idempotency():
    """
    Tests that duplicate dispatches bearing the same idempotency key
    return the exact cached acknowledgement without creating duplicate actions.
    """
    async def _run():
        adapter = SandboxBankAdapter()
        esc, bank = make_dummy_escalation()

        # 1. First Dispatch
        res1 = await adapter.submit_alert(esc, bank)
        assert res1["success"] is True
        assert res1["http_status_code"] == 202
        assert res1["details"]["is_duplicate"] is False
        assert res1["details"]["institution_mode"] == "SIMULATED_INSTITUTIONAL_SANDBOX"
        first_ref = res1["bank_reference"]

        # 2. Second Dispatch (Retry with SAME idempotency key)
        res2 = await adapter.submit_alert(esc, bank)
        assert res2["success"] is True
        assert res2["details"]["is_duplicate"] is True
        assert res2["bank_reference"] == first_ref, "Retry must return identical bank reference!"
        assert res2["details"]["attempt_count"] == 2

    asyncio.run(_run())


# ── 2. Failure Injection Scenario Tests ───────────────────────────────────

def test_sandbox_failure_scenario_429_rate_limiting():
    """Verifies that RATE_LIMITED_429 scenario raises ConnectionRefusedError."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.RATE_LIMITED_429)
        esc, bank = make_dummy_escalation()

        with pytest.raises(ConnectionRefusedError) as exc_info:
            await adapter.submit_alert(esc, bank)
        assert "429 Too Many Requests" in str(exc_info.value)

    asyncio.run(_run())


def test_sandbox_failure_scenario_500_server_error():
    """Verifies that SERVER_ERROR_500 scenario raises RuntimeError."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.SERVER_ERROR_500)
        esc, bank = make_dummy_escalation()

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.submit_alert(esc, bank)
        assert "500 Internal Server Error" in str(exc_info.value)

    asyncio.run(_run())


def test_sandbox_failure_scenario_504_timeout():
    """Verifies that TIMEOUT_504 scenario raises TimeoutError."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.TIMEOUT_504)
        esc, bank = make_dummy_escalation()

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.submit_alert(esc, bank)
        assert "504 Gateway Timeout" in str(exc_info.value)

    asyncio.run(_run())


def test_sandbox_failure_scenario_connection_reset():
    """Verifies that CONNECTION_RESET scenario raises ConnectionResetError."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.CONNECTION_RESET)
        esc, bank = make_dummy_escalation()

        with pytest.raises(ConnectionResetError) as exc_info:
            await adapter.submit_alert(esc, bank)
        assert "reset by peer" in str(exc_info.value)

    asyncio.run(_run())


def test_sandbox_failure_scenario_invalid_auth():
    """Verifies that INVALID_AUTH scenario raises PermissionError (401)."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.INVALID_AUTH)
        esc, bank = make_dummy_escalation()

        with pytest.raises(PermissionError) as exc_info:
            await adapter.submit_alert(esc, bank)
        assert "401 Unauthorized" in str(exc_info.value)

    asyncio.run(_run())


def test_sandbox_failure_scenario_malformed_response():
    """Verifies that MALFORMED_RESPONSE scenario returns unexpected structure."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.MALFORMED_RESPONSE)
        esc, bank = make_dummy_escalation()

        res = await adapter.submit_alert(esc, bank)
        assert res.get("missing_required_keys") is True

    asyncio.run(_run())


def test_sandbox_conflicting_financial_response():
    """Verifies that CONFLICTING_FINANCIAL scenario returns flagged conflicting amounts."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.CONFLICTING_FINANCIAL)
        esc, bank = make_dummy_escalation()

        res = await adapter.submit_alert(esc, bank)
        assert res["success"] is True
        assert res["details"]["scenario"] == SandboxScenario.CONFLICTING_FINANCIAL
        assert res["funds_frozen_amount"] > res["details"]["original_amount"]

    asyncio.run(_run())


def test_sandbox_partial_freeze():
    """Verifies that PARTIAL_FREEZE scenario returns valid partial hold amount."""
    async def _run():
        adapter = SandboxBankAdapter()
        adapter.set_scenario(SandboxScenario.PARTIAL_FREEZE)
        esc, bank = make_dummy_escalation()

        res = await adapter.submit_alert(esc, bank)
        assert res["success"] is True
        assert res["details"]["scenario"] == SandboxScenario.PARTIAL_FREEZE
        assert res["funds_frozen_amount"] < res["details"]["original_amount"]

    asyncio.run(_run())


# ── 3. Bank Callback Webhook Verification Tests ───────────────────────────

def test_sandbox_callback_valid_hmac_and_nonce():
    """Validates callback verification accepts authentic signed payload."""
    payload = {"alert_reference": "DR-ALERT-TEST-001", "status": "CONFIRMED"}
    raw_bytes = json.dumps(payload, sort_keys=True).encode()
    now_ts = str(time.time())
    canonical = f"{now_ts}.{raw_bytes.decode()}"
    sig = mock_bank_service.sign_payload(canonical)

    is_valid, err = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce="NONCE-TEST-001",
        payload_bytes=raw_bytes,
        signature=sig,
        timestamp_str=now_ts
    )
    assert is_valid is True
    assert err is None


def test_sandbox_callback_rejected_on_corrupt_signature():
    """Validates callback verification rejects forged HMAC signature."""
    payload = {"alert_reference": "DR-ALERT-TEST-001", "status": "CONFIRMED"}
    raw_bytes = json.dumps(payload, sort_keys=True).encode()
    now_ts = str(time.time())

    is_valid, err = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce="NONCE-TEST-002",
        payload_bytes=raw_bytes,
        signature="FORGED_INVALID_SIGNATURE",
        timestamp_str=now_ts
    )
    assert is_valid is False
    assert "Cryptographic HMAC-SHA256 signature verification failed" in err


def test_sandbox_callback_rejected_on_clock_skew():
    """Validates callback verification rejects timestamps skewed > 300 seconds."""
    payload = {"alert_reference": "DR-ALERT-TEST-001", "status": "CONFIRMED"}
    raw_bytes = json.dumps(payload, sort_keys=True).encode()
    stale_ts = str(time.time() - 3600.0) # 1 hour stale
    canonical = f"{stale_ts}.{raw_bytes.decode()}"
    sig = mock_bank_service.sign_payload(canonical)

    is_valid, err = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce="NONCE-TEST-003",
        payload_bytes=raw_bytes,
        signature=sig,
        timestamp_str=stale_ts
    )
    assert is_valid is False
    assert "Clock skew" in err


def test_sandbox_callback_rejected_on_duplicate_nonce_replay():
    """Validates callback verification rejects duplicate nonce (replay attack)."""
    payload = {"alert_reference": "DR-ALERT-TEST-001", "status": "CONFIRMED"}
    raw_bytes = json.dumps(payload, sort_keys=True).encode()
    now_ts = str(time.time())
    canonical = f"{now_ts}.{raw_bytes.decode()}"
    sig = mock_bank_service.sign_payload(canonical)

    # First attempt: succeeds
    ok1, _ = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce="NONCE-REPLAY-999",
        payload_bytes=raw_bytes,
        signature=sig,
        timestamp_str=now_ts
    )
    assert ok1 is True

    # Replay with identical nonce: rejected
    ok2, err2 = mock_bank_service.verify_and_record_callback(
        bank_code="SBIN",
        nonce="NONCE-REPLAY-999",
        payload_bytes=raw_bytes,
        signature=sig,
        timestamp_str=now_ts
    )
    assert ok2 is False
    assert "replay detected" in err2
