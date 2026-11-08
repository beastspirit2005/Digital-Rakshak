import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from domain.models.bank import (
    FraudResponseStage,
    FraudResponseLifecycleEvent,
    EscalationStatus
)
from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine, GENESIS_HASH
from domain.services.financial_reconciliation_service import (
    FinancialReconciliationService,
    FinancialInvariantViolationError
)


def test_compute_event_hash_deterministic():
    h1 = FraudLifecycleEngine.compute_event_hash(
        previous_hash=GENESIS_HASH,
        correlation_id="CORR-TEST-001",
        stage=FraudResponseStage.FRAUD_REPORTED.value,
        actor="CITIZEN_PORTAL",
        timestamp_iso="2026-11-08T22:00:00+00:00",
        metadata={"scam_type": "JOB_SCAM"}
    )
    h2 = FraudLifecycleEngine.compute_event_hash(
        previous_hash=GENESIS_HASH,
        correlation_id="CORR-TEST-001",
        stage=FraudResponseStage.FRAUD_REPORTED.value,
        actor="CITIZEN_PORTAL",
        timestamp_iso="2026-11-08T22:00:00+00:00",
        metadata={"scam_type": "JOB_SCAM"}
    )
    assert h1 == h2
    assert len(h1) == 64


def test_hash_chain_sequential_integrity():
    # Build simulated 3-event chain in memory
    events = []
    prev_hash = GENESIS_HASH
    stages = [
        FraudResponseStage.FRAUD_REPORTED,
        FraudResponseStage.TRANSACTION_IDENTIFIED,
        FraudResponseStage.BANKS_RESOLVED
    ]

    for stage in stages:
        ts = datetime.now(timezone.utc).isoformat()
        cur_hash = FraudLifecycleEngine.compute_event_hash(
            previous_hash=prev_hash,
            correlation_id="CORR-TEST-002",
            stage=stage.value,
            actor="SYSTEM_ENGINE",
            timestamp_iso=ts,
            metadata={"step": stage.value}
        )
        ev = FraudResponseLifecycleEvent(
            id=uuid.uuid4(),
            correlation_id="CORR-TEST-002",
            case_id=uuid.uuid4(),
            stage=stage.value,
            previous_stage=events[-1].stage if events else None,
            actor_or_service="SYSTEM_ENGINE",
            transition_reason=f"Transition to {stage.value}",
            metadata_payload={"step": stage.value},
            event_hash=cur_hash,
            previous_event_hash=prev_hash,
            created_at=datetime.fromisoformat(ts)
        )
        events.append(ev)
        prev_hash = cur_hash

    assert len(events) == 3
    assert events[0].previous_event_hash == GENESIS_HASH
    assert events[1].previous_event_hash == events[0].event_hash
    assert events[2].previous_event_hash == events[1].event_hash


def test_financial_invariants_valid_reconciliation():
    # Valid scenario: Reported 100k, Identified 100k, Lien 30k, Frozen 70k, Recovered 25k
    FinancialReconciliationService.validate_invariants(
        reported_loss=Decimal("100000.00"),
        identified_amount=Decimal("100000.00"),
        amount_under_lien=Decimal("30000.00"),
        amount_frozen=Decimal("70000.00"),
        amount_recovered=Decimal("25000.00")
    )


def test_financial_invariants_fail_closed_on_over_recovery():
    # Recovered 50k, but only 30k secured under lien/freeze -> MUST FAIL CLOSED
    with pytest.raises(FinancialInvariantViolationError) as exc_info:
        FinancialReconciliationService.validate_invariants(
            reported_loss=Decimal("100000.00"),
            identified_amount=Decimal("100000.00"),
            amount_under_lien=Decimal("10000.00"),
            amount_frozen=Decimal("20000.00"),
            amount_recovered=Decimal("50000.00")
        )
    assert "cannot exceed funds secured" in str(exc_info.value)


def test_financial_invariants_fail_closed_on_over_seizure():
    # Identified 50k, but cumulative secured 60k (30k lien + 30k frozen) -> MUST FAIL CLOSED
    with pytest.raises(FinancialInvariantViolationError) as exc_info:
        FinancialReconciliationService.validate_invariants(
            reported_loss=Decimal("50000.00"),
            identified_amount=Decimal("50000.00"),
            amount_under_lien=Decimal("30000.00"),
            amount_frozen=Decimal("30000.00"),
            amount_recovered=Decimal("0.00")
        )
    assert "cannot exceed identified transfer" in str(exc_info.value)


def test_financial_invariants_fail_closed_on_negative():
    with pytest.raises(FinancialInvariantViolationError) as exc_info:
        FinancialReconciliationService.validate_invariants(
            reported_loss=Decimal("50000.00"),
            identified_amount=Decimal("50000.00"),
            amount_under_lien=Decimal("-500.00"),
            amount_frozen=Decimal("0.00"),
            amount_recovered=Decimal("0.00")
        )
    assert "cannot be negative" in str(exc_info.value)
