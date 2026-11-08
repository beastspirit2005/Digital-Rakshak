import pytest
import uuid
import asyncio
from domain.models.bank import (
    ApprovalTier,
    BankRegistry,
    FinancialTransaction,
    BankIntegrationType,
    EscalationRole,
    BankEscalation,
    EscalationStatus
)
from domain.models.case import Case, CasePriority
from domain.services.approval_policy import ApprovalPolicyEngine
from domain.services.bank_integration_gateway import SandboxBankAdapter


def test_approval_policy_automated_tier():
    case = Case(
        case_number="CASE-TEST-001",
        estimated_amount=15000.0,
        priority=CasePriority.medium,
        is_ongoing_fraud=False
    )
    txn = FinancialTransaction(
        amount=15000.0,
        transaction_reference="987654321012"
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
        escalation_role=EscalationRole.BENEFICIARY_BANK.value
    )

    assert tier == ApprovalTier.AUTOMATED
    assert can_auto is True
    assert len(reasons) > 0


def test_approval_policy_investigator_tier():
    case = Case(
        case_number="CASE-TEST-002",
        estimated_amount=75000.0,
        priority=CasePriority.high,
        is_ongoing_fraud=False
    )
    txn = FinancialTransaction(
        amount=75000.0,
        transaction_reference="987654321012"
    )
    bank = BankRegistry(
        bank_code="SBIN",
        bank_name="State Bank of India",
        is_active=True,
        integration_type=BankIntegrationType.SANDBOX_API.value
    )

    tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
        case=case,
        transaction=txn,
        target_bank=bank,
        escalation_role=EscalationRole.VICTIM_BANK.value
    )

    assert tier == ApprovalTier.INVESTIGATOR_APPROVED
    assert can_auto is False


def test_approval_policy_senior_officer_tier():
    case = Case(
        case_number="CASE-TEST-003",
        estimated_amount=500000.0,
        priority=CasePriority.critical,
        is_ongoing_fraud=True
    )
    txn = FinancialTransaction(
        amount=500000.0,
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
        escalation_role=EscalationRole.BENEFICIARY_BANK.value
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
        amount=10000.0,
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
        alert_payload=payload,
        idempotency_key="TEST-IDEMP-001"
    )

    # Drive coroutine directly
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
    assert res["details"]["signature_verified"] is True
