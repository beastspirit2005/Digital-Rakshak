import pytest
import uuid
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from domain.models.bank import (
    ApprovalTier,
    BankRegistry,
    FinancialTransaction,
    BankIntegrationType,
    EscalationRole,
    BankEscalation,
    EscalationStatus,
    BankInstructionCategory
)
from domain.models.case import Case, CasePriority
from domain.services.approval_policy import ApprovalPolicyEngine
from domain.services.bank_integration_gateway import SandboxBankAdapter, BankIntegrationGateway


def test_approval_policy_automated_informational_alert():
    # Informational Alert below threshold, recent, with valid UTR is eligible for automated dispatch
    case = Case(
        case_number="CASE-TEST-001",
        estimated_amount=15000.0,
        priority=CasePriority.medium,
        is_ongoing_fraud=False,
        created_at=datetime.now(timezone.utc)
    )
    txn = FinancialTransaction(
        amount=Decimal("15000.00"),
        transaction_reference="987654321012",
        transaction_time=datetime.now(timezone.utc)
    )
    bank = BankRegistry(
        bank_code="HDFC",
        bank_name="HDFC Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.VICTIM_BANK.value,
        instruction_category=BankInstructionCategory.INFORMATIONAL_ALERT.value
    )

    assert tier == ApprovalTier.AUTOMATED
    assert can_auto is True
    assert len(reasons) > 0


def test_freeze_and_lien_never_automated():
    # Statutory account freeze / protective hold under Section 106 BNSS MUST NEVER be auto-dispatched
    case = Case(
        case_number="CASE-TEST-001B",
        estimated_amount=5000.0,
        priority=CasePriority.low,
        is_ongoing_fraud=False,
        created_at=datetime.now(timezone.utc)
    )
    txn = FinancialTransaction(
        amount=Decimal("5000.00"),
        transaction_reference="987654321012",
        transaction_time=datetime.now(timezone.utc)
    )
    bank = BankRegistry(
        bank_code="HDFC",
        bank_name="HDFC Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.BENEFICIARY_BANK.value,
        instruction_category=BankInstructionCategory.STATUTORY_FREEZE_ORDER.value
    )

    assert tier == ApprovalTier.INVESTIGATOR_APPROVED
    assert can_auto is False
    assert any("Section 106 BNSS" in r for r in reasons)


def test_automated_dispatch_rejects_stale_transactions():
    # Stale transactions (>48h) must NOT be auto-dispatched
    stale_time = datetime.now(timezone.utc) - timedelta(hours=72)
    case = Case(
        case_number="CASE-TEST-STALE",
        estimated_amount=10000.0,
        priority=CasePriority.low,
        created_at=stale_time
    )
    txn = FinancialTransaction(
        amount=Decimal("10000.00"),
        transaction_reference="987654321012",
        transaction_time=stale_time
    )
    bank = BankRegistry(
        bank_code="HDFC",
        bank_name="HDFC Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.VICTIM_BANK.value,
        instruction_category=BankInstructionCategory.INFORMATIONAL_ALERT.value
    )

    assert can_auto is False
    assert tier == ApprovalTier.INVESTIGATOR_APPROVED


def test_approval_policy_senior_officer_tier():
    case = Case(
        case_number="CASE-TEST-003",
        estimated_amount=500000.0,
        priority=CasePriority.critical,
        is_ongoing_fraud=True
    )
    txn = FinancialTransaction(
        amount=Decimal("500000.00"),
        transaction_reference="123456789012"
    )
    bank = BankRegistry(
        bank_code="ICIC",
        bank_name="ICICI Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.BENEFICIARY_BANK.value,
        instruction_category=BankInstructionCategory.STATUTORY_FREEZE_ORDER.value
    )

    assert tier == ApprovalTier.SENIOR_OFFICER
    assert can_auto is False


def test_approval_policy_mule_ring_escalation():
    case = Case(
        case_number="CASE-TEST-004",
        estimated_amount=10000.0,
        priority=CasePriority.low
    )
    txn = FinancialTransaction(
        amount=Decimal("10000.00"),
        transaction_reference="123456789012"
    )
    bank = BankRegistry(
        bank_code="AXIS",
        bank_name="Axis Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.BENEFICIARY_BANK.value,
        is_mule_ring_suspect=True
    )

    assert tier == ApprovalTier.SENIOR_OFFICER
    assert can_auto is False
    assert any("mule" in r.lower() for r in reasons)


def test_sandbox_bank_adapter_dispatch():
    adapter = SandboxBankAdapter()
    bank = BankRegistry(
        bank_code="HDFC",
        bank_name="HDFC Bank",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )
    payload = {
        "alert_reference": "DR-ALERT-20261105-TEST01",
        "case_number": "CASE-2026-999",
        "amount": 25000.0
    }
    esc = BankEscalation(
        alert_reference="DR-ALERT-20261105-TEST01",
        escalation_role=EscalationRole.BENEFICIARY_BANK.value,
        instruction_category=BankInstructionCategory.PROTECTIVE_HOLD_REQUEST.value,
        statutory_basis="BNSS_2023_SECTION_106_PROTECTIVE_HOLD",
        alert_payload=payload,
        idempotency_key="TEST-IDEMP-001"
    )

    coro = adapter.submit_alert(esc, bank)
    try:
        coro.send(None)
    except StopIteration as e:
        res = e.value
    finally:
        coro.close()

    assert res["success"] is True
    assert res["http_status_code"] == 202
    assert "ACK-HDFC" in res["bank_reference"]
    assert res["response_type"] == "ACKNOWLEDGEMENT"
    assert res["details"]["idempotency_key"] == "TEST-IDEMP-001"


def test_callback_replay_window_validation():
    # Fresh callback within 300s window -> ACCEPTED
    payload_bytes = b'{"status":"PROCESSED"}'
    secret = "dr_sandbox_secret"
    fresh_time = datetime.now(timezone.utc).isoformat()
    canonical = f"{fresh_time}.{payload_bytes.decode()}"
    sig = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()

    is_valid, err = BankIntegrationGateway.verify_callback_authenticity(
        payload_bytes=payload_bytes,
        signature=sig,
        timestamp_str=fresh_time,
        secret_key=secret
    )
    assert is_valid is True
    assert err is None

    # Stale callback (10 minutes old > 300s) -> REJECTED
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    stale_canonical = f"{stale_time}.{payload_bytes.decode()}"
    stale_sig = hmac.new(secret.encode(), stale_canonical.encode(), hashlib.sha256).hexdigest()

    is_valid_stale, err_stale = BankIntegrationGateway.verify_callback_authenticity(
        payload_bytes=payload_bytes,
        signature=stale_sig,
        timestamp_str=stale_time,
        secret_key=secret
    )
    assert is_valid_stale is False
    assert "replay window" in err_stale
