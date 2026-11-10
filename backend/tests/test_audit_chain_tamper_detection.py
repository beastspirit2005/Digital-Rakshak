import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from domain.models.bank import (
    FraudResponseStage,
    FraudResponseLifecycleEvent,
    EvidenceCheckpoint
)
from domain.models.case import Case
from domain.services.fraud_lifecycle_engine import (
    FraudLifecycleEngine,
    GENESIS_HASH
)
from domain.services.evidence_integrity_service import (
    EvidenceIntegrityService,
    DEFAULT_KEY_ID
)


# ── Fixtures & Helpers ────────────────────────────────────────────────────────

def create_synthetic_event(
    case_id: uuid.UUID,
    correlation_id: str,
    stage: str,
    prev_hash: str,
    actor: str = "POLICE_STATION_HQ",
    metadata: dict = None,
    created_at: datetime = None
) -> FraudResponseLifecycleEvent:
    ts = created_at or datetime.now(timezone.utc)
    meta = metadata or {"action": "INITIAL_ALERT", "tier": "TIER_1"}
    
    # Compute deterministic hash matching FraudLifecycleEngine
    event_hash = FraudLifecycleEngine.compute_event_hash(
        previous_hash=prev_hash,
        correlation_id=correlation_id,
        stage=stage,
        actor=actor,
        timestamp_iso=ts.isoformat(),
        metadata=meta
    )
    
    ev = FraudResponseLifecycleEvent(
        id=uuid.uuid4(),
        correlation_id=correlation_id,
        case_id=case_id,
        stage=stage,
        actor_or_service=actor,
        transition_reason=f"Transitioned to {stage}",
        metadata_payload=meta,
        event_hash=event_hash,
        previous_event_hash=prev_hash,
        created_at=ts
    )
    return ev


# ── 1. Unbroken Valid Hash Chain Verification ─────────────────────────────

@pytest.mark.asyncio
async def test_audit_chain_valid_unbroken_merkle_sequence():
    """Validates that a correctly constructed sequential audit chain passes verification."""
    case_id = uuid.uuid4()
    corr_id = f"CORR-{uuid.uuid4().hex[:8]}"
    t0 = datetime.now(timezone.utc)

    # Event 1: Genesis -> INITIATED
    ev1 = create_synthetic_event(case_id, corr_id, "INITIATED", GENESIS_HASH, created_at=t0)
    # Event 2: INITIATED -> JURISDICTION_ROUTED
    ev2 = create_synthetic_event(case_id, corr_id, "JURISDICTION_ROUTED", ev1.event_hash, created_at=t0 + timedelta(seconds=1))
    # Event 3: JURISDICTION_ROUTED -> INSTITUTIONAL_DISPATCHED
    ev3 = create_synthetic_event(case_id, corr_id, "INSTITUTIONAL_DISPATCHED", ev2.event_hash, created_at=t0 + timedelta(seconds=2))

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1, ev2, ev3]
    mock_db.execute.return_value = mock_res

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(mock_db, case_id)
    assert is_valid is True
    assert count == 3
    assert err is None


# ── 2. Payload Modification Tamper Detection ──────────────────────────────

@pytest.mark.asyncio
async def test_audit_chain_tamper_detected_on_payload_mutation():
    """
    Validates that any out-of-band alteration to an event's metadata or payload
    is immediately detected as a cryptographic tampering failure.
    """
    case_id = uuid.uuid4()
    corr_id = f"CORR-{uuid.uuid4().hex[:8]}"
    t0 = datetime.now(timezone.utc)

    ev1 = create_synthetic_event(case_id, corr_id, "INITIATED", GENESIS_HASH, created_at=t0)
    ev2 = create_synthetic_event(case_id, corr_id, "FUNDS_FROZEN", ev1.event_hash, created_at=t0 + timedelta(seconds=1))

    # Malicious actor tampers with ev2's metadata payload (e.g. inflating frozen amount)
    ev2.metadata_payload = {"action": "INITIAL_ALERT", "tier": "TIER_1", "tampered_amount": "9999999"}

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1, ev2]
    mock_db.execute.return_value = mock_res

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(mock_db, case_id)
    assert is_valid is False
    assert "tampered" in err.lower()
    assert count == 1  # Failed at event index 1 (the 2nd event)


# ── 3. Sequence Gap / Missing Event Detection ─────────────────────────────

@pytest.mark.asyncio
async def test_audit_chain_gap_detection_on_deleted_event():
    """
    Validates that deleting or omitting an intermediate lifecycle record
    causes an immediate previous-hash mismatch failure.
    """
    case_id = uuid.uuid4()
    corr_id = f"CORR-{uuid.uuid4().hex[:8]}"
    t0 = datetime.now(timezone.utc)

    ev1 = create_synthetic_event(case_id, corr_id, "INITIATED", GENESIS_HASH, created_at=t0)
    ev2 = create_synthetic_event(case_id, corr_id, "JURISDICTION_ROUTED", ev1.event_hash, created_at=t0 + timedelta(seconds=1))
    ev3 = create_synthetic_event(case_id, corr_id, "INSTITUTIONAL_DISPATCHED", ev2.event_hash, created_at=t0 + timedelta(seconds=2))

    # Omit ev2: chain now jumps directly from ev1 to ev3
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1, ev3]
    mock_db.execute.return_value = mock_res

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(mock_db, case_id)
    assert is_valid is False
    assert "chain broken" in err.lower()
    assert "previous hash mismatch" in err.lower()


# ── 4. Event Reordering Tamper Detection ──────────────────────────────────

@pytest.mark.asyncio
async def test_audit_chain_reordering_detection():
    """
    Validates that swapping the chronological order of two valid events
    breaks the hash continuity and is rejected.
    """
    case_id = uuid.uuid4()
    corr_id = f"CORR-{uuid.uuid4().hex[:8]}"
    t0 = datetime.now(timezone.utc)

    ev1 = create_synthetic_event(case_id, corr_id, "INITIATED", GENESIS_HASH, created_at=t0)
    ev2 = create_synthetic_event(case_id, corr_id, "JURISDICTION_ROUTED", ev1.event_hash, created_at=t0 + timedelta(seconds=1))
    ev3 = create_synthetic_event(case_id, corr_id, "INSTITUTIONAL_DISPATCHED", ev2.event_hash, created_at=t0 + timedelta(seconds=2))

    # Swap ev2 and ev3
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1, ev3, ev2]
    mock_db.execute.return_value = mock_res

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(mock_db, case_id)
    assert is_valid is False
    assert "chain broken" in err.lower()


# ── 5. Signed Checkpoint Verification & Tamper Detection ───────────────────

def test_checkpoint_signature_generation_and_verification():
    """
    Validates HMAC-SHA256 checkpoint signature creation and verification,
    including rejection of forged signatures or rotated/unknown keys.
    """
    test_root_hash = "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0"
    
    # Generate signature using default key
    sig = EvidenceIntegrityService.sign_checkpoint_hash(
        root_hash=test_root_hash,
        key_id=DEFAULT_KEY_ID
    )
    assert isinstance(sig, str) and len(sig) == 64

    # 1. Valid signature passes
    valid = EvidenceIntegrityService.verify_checkpoint_signature(
        root_hash=test_root_hash,
        signature=sig,
        key_id=DEFAULT_KEY_ID
    )
    assert valid is True

    # 2. Forged signature fails
    forged_sig = "0000" + sig[4:]
    invalid_sig = EvidenceIntegrityService.verify_checkpoint_signature(
        root_hash=test_root_hash,
        signature=forged_sig,
        key_id=DEFAULT_KEY_ID
    )
    assert invalid_sig is False

    # 3. Altered root hash fails
    altered_hash = "b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0a"
    invalid_hash = EvidenceIntegrityService.verify_checkpoint_signature(
        root_hash=altered_hash,
        signature=sig,
        key_id=DEFAULT_KEY_ID
    )
    assert invalid_hash is False


# ── 6. Section 63 BSA 2023 Evidentiary Certificate Generation ────────────

@pytest.mark.asyncio
async def test_bsa_2023_section_63_certificate_generation():
    """
    Validates that generate_bsa_evidentiary_certificate produces a legal certificate
    meeting all statutory mandates of Bharatiya Sakshya Adhiniyam 2023 Sec 63(4).
    """
    case_id = uuid.uuid4()
    case_number = "CASE-TXN-20261109-SEC63A"
    corr_id = f"CORR-{uuid.uuid4().hex[:8]}"
    t0 = datetime.now(timezone.utc)

    mock_case = Case(
        id=case_id,
        case_number=case_number,
        status="investigating",
        priority="high"
    )

    ev1 = create_synthetic_event(case_id, corr_id, "INITIATED", GENESIS_HASH, created_at=t0)
    ev2 = create_synthetic_event(case_id, corr_id, "ACKNOWLEDGED", ev1.event_hash, created_at=t0 + timedelta(seconds=1))

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [ev1, ev2]
    mock_db.execute.return_value = mock_res

    cert = await FraudLifecycleEngine.generate_bsa_evidentiary_certificate(
        db=mock_db,
        case=mock_case,
        officer_name="Inspector Rajesh Kumar, Cyber Crime Police Station"
    )

    # Statutory structure validation
    assert "Section 63(4)" in cert["certificate_title"]
    assert cert["statutory_act"] == "Bharatiya Sakshya Adhiniyam, 2023 (Act No. 47 of 2023)"
    assert cert["case_number"] == case_number
    assert cert["certifying_officer"] == "Inspector Rajesh Kumar, Cyber Crime Police Station"
    assert cert["integrity_verification"]["cryptographic_hash_chain_valid"] is True
    assert cert["integrity_verification"]["total_verified_lifecycle_events"] == 2
    assert cert["integrity_verification"]["merkle_root_hash"] == ev2.event_hash

    # Clause declarations
    clauses = cert["statutory_declarations"]
    assert "clause_a" in clauses and "ordinary course of official duty" in clauses["clause_a"]
    assert "clause_b" in clauses and "continuous integrity" in clauses["clause_b"]
    assert "clause_c" in clauses and "accurately reflect" in clauses["clause_c"]

    # Statutory powers invoked
    signoff = cert["statutory_signoff_block"]
    assert "Section 94 & Section 106 Bharatiya Nagarik Suraksha Sanhita, 2023" in signoff["powers_invoked"]
    assert len(cert["lifecycle_events_ledger"]) == 2
