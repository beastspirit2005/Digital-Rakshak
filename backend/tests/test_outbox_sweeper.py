import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from core.config import settings
from domain.models.bank import (
    InstitutionalOutboxEvent,
    OutboxWorkerRun,
    BankEscalation,
    EscalationStatus
)
from domain.services.outbox_worker import OutboxWorker, RETRY_SCHEDULE_SECONDS, MAX_DISPATCH_ATTEMPTS
from api.v1.internal_sweeper import verify_scheduler_secret


# ── 1. Scheduler Secret Authentication Tests ──────────────────────────────

def test_scheduler_secret_auth_valid_bearer():
    """Validates that Authorization: Bearer <CRON_SECRET> is accepted."""
    secret = settings.CRON_SECRET
    # Should not raise exception
    verify_scheduler_secret(authorization=f"Bearer {secret}")


def test_scheduler_secret_auth_valid_header():
    """Validates that X-Cron-Secret: <CRON_SECRET> is accepted."""
    secret = settings.CRON_SECRET
    verify_scheduler_secret(x_cron_secret=secret)


def test_scheduler_secret_auth_valid_query_param():
    """Validates that ?token=<CRON_SECRET> is accepted."""
    secret = settings.CRON_SECRET
    verify_scheduler_secret(token=secret)


def test_scheduler_secret_auth_invalid_token():
    """Validates that wrong token raises 401 Unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        verify_scheduler_secret(authorization="Bearer wrong_token_value_here")
    assert exc_info.value.status_code == 401
    assert "Unauthorized" in exc_info.value.detail


def test_scheduler_secret_auth_missing_credentials():
    """Validates that missing authorization raises 401 Unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        verify_scheduler_secret()
    assert exc_info.value.status_code == 401


# ── 2. Lease Expiry Recovery Tests ────────────────────────────────────────

def test_lease_expiry_recovery_resets_stale_events():
    """
    Tests that events in 'PROCESSING' whose lease_expires_at is in the past
    are safely recovered and transitioned to 'RETRY_SCHEDULED'.
    """
    async def _run():
        worker = OutboxWorker(worker_id="WORKER-TEST-LEASE")
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(seconds=60)

        # Mock expired event
        stale_event = InstitutionalOutboxEvent(
            id=uuid.uuid4(),
            event_type="BANK_ESCALATION_DISPATCH",
            aggregate_id=uuid.uuid4(),
            correlation_id="CORR-STALE-TEST",
            status="PROCESSING",
            locked_by="OLD_CRASHED_WORKER",
            locked_at=now - timedelta(minutes=5),
            lease_expires_at=expired_time,
            attempt_count=1
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stale_event]
        mock_db.execute.return_value = mock_result

        recovered_count = await worker.recover_expired_leases(mock_db, now=now)

        assert recovered_count == 1
        assert stale_event.status == "RETRY_SCHEDULED"
        assert stale_event.locked_by is None
        assert stale_event.lease_expires_at is None
        assert stale_event.last_error_code == "LEASE_EXPIRED_RECOVERED"
        assert stale_event.available_at == now
        assert mock_db.commit.called

    asyncio.run(_run())


# ── 3. Backoff Jitter Calculation Tests ───────────────────────────────────

def test_backoff_jitter_adheres_to_schedule():
    """Verifies backoff delays match schedule with uniform +/- 10% jitter."""
    worker = OutboxWorker()
    for attempt, base_sec in RETRY_SCHEDULE_SECONDS.items():
        delays = [worker.calculate_backoff(attempt) for _ in range(50)]
        for d in delays:
            # 90% of base <= d <= 110% of base
            lower = max(1, int(base_sec * 0.9))
            upper = max(1, int(base_sec * 1.1) + 1)
            assert lower <= d <= upper, f"Delay {d} out of range for base {base_sec}"


# ── 4. Failure Handling & Dead-Letter Progression Tests ───────────────────

def test_failure_handling_retries_then_dead_letters():
    """
    Verifies that errors on attempts 1..4 result in RETRY_SCHEDULED,
    while attempt 5 transitions to DEAD_LETTER and marks escalation as DEAD_LETTER.
    """
    async def _run():
        worker = OutboxWorker(worker_id="WORKER-TEST-FAILURES")
        escalation_id = uuid.uuid4()

        event = InstitutionalOutboxEvent(
            id=uuid.uuid4(),
            event_type="BANK_ESCALATION_DISPATCH",
            aggregate_id=escalation_id,
            correlation_id="CORR-FAIL-TEST",
            status="PROCESSING",
            attempt_count=0
        )

        mock_db = AsyncMock()

        # Attempts 1 to 4 -> RETRY_SCHEDULED
        for attempt in range(1, MAX_DISPATCH_ATTEMPTS):
            res = await worker._handle_failure(mock_db, event, f"Simulated error {attempt}")
            assert res["success"] is False
            assert res["attempt_count"] == attempt
            assert res["is_dead_letter"] is False
            assert event.status == "RETRY_SCHEDULED"
            assert event.last_error_code == "DISPATCH_FAILED"
            assert event.locked_by is None

        # Attempt 5 -> DEAD_LETTER
        mock_esc = BankEscalation(
            id=escalation_id,
            status=EscalationStatus.READY.value
        )
        mock_esc_result = MagicMock()
        mock_esc_result.scalar_one_or_none.return_value = mock_esc
        mock_db.execute.return_value = mock_esc_result

        res_5 = await worker._handle_failure(mock_db, event, "Final connection failure")
        assert res_5["is_dead_letter"] is True
        assert event.status == "DEAD_LETTER"
        assert event.last_error_code == "MAX_ATTEMPTS_EXHAUSTED"
        assert mock_esc.status == EscalationStatus.DEAD_LETTER.value

    asyncio.run(_run())


# ── 5. Outbox Worker Run Audit Record Tests ───────────────────────────────

def test_outbox_worker_run_model_initialization():
    """Verifies OutboxWorkerRun fields and default values."""
    run = OutboxWorkerRun(
        id=uuid.uuid4(),
        worker_id="WORKER-AUDIT-TEST",
        trigger_type="CRON",
        status="SUCCESS",
        events_claimed=5,
        events_processed=4,
        events_retry_scheduled=1,
        events_dead_lettered=0,
        duration_ms=1250
    )
    assert run.worker_id == "WORKER-AUDIT-TEST"
    assert run.trigger_type == "CRON"
    assert run.status == "SUCCESS"
    assert run.events_claimed == 5
    assert run.events_processed == 4
    assert run.duration_ms == 1250
