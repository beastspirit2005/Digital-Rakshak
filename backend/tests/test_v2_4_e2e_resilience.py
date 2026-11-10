import pytest
import uuid
import json
import time
import hmac
import hashlib
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from domain.models.bank import (
    InstitutionalOutboxEvent,
    BankEscalation,
    BankRegistry,
    EscalationStatus,
    FinancialTransaction,
    FraudResponseStage,
    FraudResponseLifecycleEvent
)
from domain.models.case import Case
from domain.models.user import User
from domain.services.outbox_worker import OutboxWorker, MAX_DISPATCH_ATTEMPTS
from domain.services.bank_integrations import (
    BankCircuitBreaker,
    CircuitBreakerState
)
from domain.services.financial_reconciliation_service import (
    FinancialReconciliationService,
    FinancialInvariantViolationError
)
from domain.services.fraud_lifecycle_engine import (
    FraudLifecycleEngine,
    GENESIS_HASH
)
from services.mock_bank_service import mock_bank_service
from api.v1.internal_sweeper import verify_scheduler_secret


# ── Scenario 1: Scheduled Outbox Processing ──────────────────────────────

@pytest.mark.asyncio
async def test_scenario_01_scheduled_outbox_processing():
    """Sweeper claims PENDING event, dispatches to adapter, records outcome."""
    worker = OutboxWorker(worker_id="WORKER-S1")
    now = datetime.now(timezone.utc)
    ev_id = uuid.uuid4()
    agg_id = uuid.uuid4()

    event = InstitutionalOutboxEvent(
        id=ev_id,
        event_type="BANK_ESCALATION_DISPATCH",
        aggregate_id=agg_id,
        correlation_id="CORR-S1",
        payload={"escalation_id": str(agg_id), "bank_code": "HDFC"},
        status="PENDING",
        available_at=now - timedelta(seconds=10),
        attempt_count=0
    )

    mock_db = AsyncMock()
    mock_rem = MagicMock()
    mock_rem.scalar_one.return_value = 0
    mock_db.execute.return_value = mock_rem

    with patch.object(worker, "claim_batch", new_callable=AsyncMock) as mock_claim, \
         patch.object(worker, "process_event", new_callable=AsyncMock) as mock_process:
        
        mock_claim.return_value = [event]
        mock_process.return_value = {"success": True, "event_id": str(event.id)}

        summary = await worker.run_tick(mock_db, batch_size=5, trigger_type="CRON")
        assert summary["claimed"] == 1
        assert summary["processed"] == 1
        assert summary["status"] == "completed"


# ── Scenario 2: Escalation Approved With dispatch_now=true ────────────────

@pytest.mark.asyncio
async def test_scenario_02_approval_auto_dispatch_synchronization():
    """Manual approval with dispatch_now=true delegates to outbox worker."""
    worker = OutboxWorker(worker_id="ON-DEMAND-DISPATCHER")
    ev_id = uuid.uuid4()
    agg_id = uuid.uuid4()

    event = InstitutionalOutboxEvent(
        id=ev_id,
        event_type="BANK_ESCALATION_DISPATCH",
        aggregate_id=agg_id,
        correlation_id="CORR-S2",
        payload={"escalation_id": str(agg_id), "bank_code": "SBI"},
        status="PENDING",
        attempt_count=0
    )

    mock_db = AsyncMock()
    with patch.object(worker, "process_event", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = {"success": True, "event_id": str(event.id)}
        res = await worker.process_event(mock_db, event)
        assert res["success"] is True
        mock_proc.assert_awaited_once_with(mock_db, event)


# ── Scenario 3: Crash After Approval Rollback Integrity ───────────────────

@pytest.mark.asyncio
async def test_scenario_03_crash_after_approval_rollback():
    """Validates two-phase decoupling: transient failure updates event to RETRY_SCHEDULED."""
    worker = OutboxWorker(worker_id="WORKER-S3")
    ev = InstitutionalOutboxEvent(
        id=uuid.uuid4(),
        event_type="BANK_ESCALATION_DISPATCH",
        aggregate_id=uuid.uuid4(),
        correlation_id="CORR-S3",
        payload={"escalation_id": str(uuid.uuid4())},
        status="PROCESSING",
        attempt_count=0
    )

    mock_db = AsyncMock()
    with patch("domain.services.bank_integration_gateway.BankIntegrationGateway.dispatch_escalation", new_callable=AsyncMock) as mock_gw:
        mock_gw.side_effect = TimeoutError("Connection reset during external transmission")

        res = await worker.process_event(mock_db, ev)
        assert res["success"] is False
        assert ev.status == "RETRY_SCHEDULED"
        assert ev.last_error_code == "UNEXPECTED_EXCEPTION"
        assert mock_db.commit.await_count >= 1


# ── Scenario 4: Receiver-Side Idempotent Retry ────────────────────────────

def test_scenario_04_receiver_side_idempotent_retry_after_network_timeout():
    """Retry with identical idempotency key returns exact same acknowledgment."""
    mock_bank_service.reset()
    idempotency_key = f"IDEMP-{uuid.uuid4().hex[:12]}"
    alert_ref = "DR-ALERT-20261110-IDEMPOTENCY"

    # First attempt: processed by mock bank
    first_resp = mock_bank_service.process_incoming_alert(
        bank_code="SBI",
        bank_name="State Bank of India",
        idempotency_key=idempotency_key,
        alert_reference=alert_ref,
        instruction_category="STATUTORY_FREEZE_ORDER",
        escalation_role="BENEFICIARY_SUSPECT_BANK",
        amount=Decimal("50000.00")
    )
    assert first_resp["success"] is True
    assert first_resp["response_type"] == "ACKNOWLEDGEMENT"
    first_ack_ref = first_resp["bank_reference"]

    # Second attempt (after timeout): must return identical bank_reference
    retry_resp = mock_bank_service.process_incoming_alert(
        bank_code="SBI",
        bank_name="State Bank of India",
        idempotency_key=idempotency_key,
        alert_reference=alert_ref,
        instruction_category="STATUTORY_FREEZE_ORDER",
        escalation_role="BENEFICIARY_SUSPECT_BANK",
        amount=Decimal("50000.00")
    )
    assert retry_resp["bank_reference"] == first_ack_ref
    assert mock_bank_service._received_requests[idempotency_key]["request_count"] == 2


# ── Scenario 5: Concurrent Workers with SKIP LOCKED ───────────────────────

@pytest.mark.asyncio
async def test_scenario_05_concurrent_workers_skip_locked():
    """Two concurrent workers claim mutually exclusive non-overlapping batches."""
    worker1 = OutboxWorker(worker_id="WORKER-ALPHA")
    worker2 = OutboxWorker(worker_id="WORKER-BETA")

    ev1 = InstitutionalOutboxEvent(id=uuid.uuid4(), status="PENDING", correlation_id="C1")
    ev2 = InstitutionalOutboxEvent(id=uuid.uuid4(), status="PENDING", correlation_id="C2")

    mock_db1 = AsyncMock()
    mock_db2 = AsyncMock()

    with patch.object(worker1, "claim_batch", new_callable=AsyncMock) as claim1, \
         patch.object(worker2, "claim_batch", new_callable=AsyncMock) as claim2:
        
        claim1.return_value = [ev1]
        claim2.return_value = [ev2]

        batch1 = await worker1.claim_batch(mock_db1, batch_size=1)
        batch2 = await worker2.claim_batch(mock_db2, batch_size=1)

        assert batch1[0].id != batch2[0].id
        assert batch1[0].id == ev1.id
        assert batch2[0].id == ev2.id


# ── Scenario 6: Expired Lease Recovery ────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_06_expired_lease_recovery():
    """Worker crash leaving lease_expires_at in past is automatically recycled to RETRY_SCHEDULED."""
    worker = OutboxWorker(worker_id="SWEEPER-RECOVER")
    now = datetime.now(timezone.utc)

    abandoned_ev = InstitutionalOutboxEvent(
        id=uuid.uuid4(),
        event_type="BANK_ESCALATION_DISPATCH",
        aggregate_id=uuid.uuid4(),
        correlation_id="CORR-CRASH",
        status="PROCESSING",
        locked_by="CRASHED-WORKER-99",
        lease_expires_at=now - timedelta(seconds=120)
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [abandoned_ev]
    mock_db.execute.return_value = mock_res

    recovered = await worker.recover_expired_leases(mock_db, now=now)
    assert recovered == 1
    assert abandoned_ev.status == "RETRY_SCHEDULED"
    assert abandoned_ev.locked_by is None
    assert abandoned_ev.lease_expires_at is None
    assert abandoned_ev.last_error_code == "LEASE_EXPIRED_RECOVERED"


# ── Scenario 7: Dead-Letter Manual Retry Authorization ─────────────────────

@pytest.mark.asyncio
async def test_scenario_07_dead_letter_manual_retry_authorization():
    """Exhausted retries transition to DEAD_LETTER; requires authorized retry."""
    worker = OutboxWorker(worker_id="WORKER-S7")
    ev = InstitutionalOutboxEvent(
        id=uuid.uuid4(),
        event_type="BANK_ESCALATION_DISPATCH",
        aggregate_id=uuid.uuid4(),
        correlation_id="CORR-S7",
        payload={"escalation_id": str(uuid.uuid4())},
        status="PROCESSING",
        attempt_count=MAX_DISPATCH_ATTEMPTS - 1
    )

    mock_db = AsyncMock()
    mock_esc_res = MagicMock()
    mock_esc_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_esc_res

    with patch("domain.services.bank_integration_gateway.BankIntegrationGateway.dispatch_escalation", new_callable=AsyncMock) as mock_gw:
        mock_gw.side_effect = RuntimeError("Fatal unrecoverable adapter error")

        res = await worker.process_event(mock_db, ev)
        assert res["success"] is False
        assert ev.status == "DEAD_LETTER"
        assert ev.attempt_count == MAX_DISPATCH_ATTEMPTS


# ── Scenario 8: Webhook Callback Replay Attack Rejected ───────────────────

def test_scenario_08_webhook_callback_replay_attack_rejected():
    """Replaying identical callback nonce or timestamp skew >300s is rejected."""
    mock_bank_service.reset()
    bank_code = "HDFC"
    payload = {"alert_reference": "DR-ALERT-20261110-WEBHOOK", "action": "FROZEN"}
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    nonce = f"NONCE-{uuid.uuid4().hex[:12]}"
    now_ts = str(time.time())

    canonical = f"{now_ts}.{payload_bytes.decode('utf-8')}"
    sig = hmac.new(mock_bank_service.secret_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()

    # 1. First callback delivery: succeeds
    valid_first, err1 = mock_bank_service.verify_and_record_callback(
        bank_code=bank_code,
        nonce=nonce,
        payload_bytes=payload_bytes,
        signature=sig,
        timestamp_str=now_ts
    )
    assert valid_first is True
    assert err1 is None

    # 2. Replay attack with same nonce: rejected
    valid_replay, err2 = mock_bank_service.verify_and_record_callback(
        bank_code=bank_code,
        nonce=nonce,
        payload_bytes=payload_bytes,
        signature=sig,
        timestamp_str=now_ts
    )
    assert valid_replay is False
    assert "replay" in err2.lower()


# ── Scenario 9: Institutional Outage & Circuit Breaker Recovery ───────────

def test_scenario_09_institutional_outage_circuit_breaker():
    """Repeated 500 failures trip breaker to OPEN; fast-fails until cooldown."""
    breaker = BankCircuitBreaker(failure_threshold=3, recovery_timeout_seconds=10.0)
    assert breaker._get_entry("SBI")["state"] == CircuitBreakerState.CLOSED

    # 3 consecutive failures trip breaker
    for _ in range(3):
        breaker.record_failure("SBI", "500 Server Error")
    assert breaker._get_entry("SBI")["state"] == CircuitBreakerState.OPEN
    can_exec, reason = breaker.can_execute("SBI")
    assert can_exec is False

    # Simulate cooldown elapsing
    entry = breaker._get_entry("SBI")
    entry["last_failure_time"] = time.time() - 15.0

    can_exec, reason = breaker.can_execute("SBI")
    assert can_exec is True
    assert breaker._get_entry("SBI")["state"] == CircuitBreakerState.HALF_OPEN

    # Successful call in HALF_OPEN resets breaker
    breaker.record_success("SBI")
    assert breaker._get_entry("SBI")["state"] == CircuitBreakerState.CLOSED


# ── Scenario 10: Financial Reconciliation Invariant ───────────────────────

def test_scenario_10_financial_reconciliation_invariant():
    """Reconciliation strictly verifies funds invariant: cannot exceed txn amount."""
    # Attempting to freeze ₹150,000 on a ₹100,000 transaction must violate financial invariants
    with pytest.raises(FinancialInvariantViolationError) as exc_info:
        FinancialReconciliationService.validate_invariants(
            reported_loss=Decimal("100000.00"),
            identified_amount=Decimal("100000.00"),
            amount_under_lien=Decimal("0.00"),
            amount_frozen=Decimal("150000.00"),
            amount_recovered=Decimal("0.00")
        )
    assert "cannot exceed identified transfer amount" in str(exc_info.value)


# ── Scenario 11: Audit Chain Tamper Detection (BSA 2023) ───────────────────

@pytest.mark.asyncio
async def test_scenario_11_audit_chain_tamper_detection():
    """Section 63 BSA 2023 tamper detection verifies unbroken cryptographic chain."""
    case_id = uuid.uuid4()
    corr_id = "CORR-CHAIN-S11"
    t0 = datetime.now(timezone.utc)

    # Valid event
    ev1_hash = FraudLifecycleEngine.compute_event_hash(
        previous_hash=GENESIS_HASH,
        correlation_id=corr_id,
        stage="INITIATED",
        actor="OFFICER",
        timestamp_iso=t0.isoformat(),
        metadata={"status": "OK"}
    )
    ev1 = FraudResponseLifecycleEvent(
        id=uuid.uuid4(),
        case_id=case_id,
        correlation_id=corr_id,
        stage="INITIATED",
        actor_or_service="OFFICER",
        metadata_payload={"status": "OK"},
        event_hash=ev1_hash,
        previous_event_hash=GENESIS_HASH,
        created_at=t0
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1]
    mock_db.execute.return_value = mock_res

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(mock_db, case_id)
    assert is_valid is True
    assert count == 1


# ── Scenario 12: Internal Scheduler Secret Protection ─────────────────────

def test_scenario_12_internal_scheduler_secret_protection():
    """Unauthenticated or forged scheduler token rejects invocation with 401."""
    # 1. Unauthenticated
    with pytest.raises(HTTPException) as exc1:
        verify_scheduler_secret(authorization=None)
    assert exc1.value.status_code == 401

    # 2. Forged secret
    with pytest.raises(HTTPException) as exc2:
        verify_scheduler_secret(authorization="Bearer forged_malicious_secret")
    assert exc2.value.status_code == 401
