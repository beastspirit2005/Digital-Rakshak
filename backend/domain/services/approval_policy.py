import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict, Any, Optional
from domain.models.bank import (
    ApprovalTier,
    BankRegistry,
    FinancialTransaction,
    BankInstructionCategory,
    ResolutionConfidenceType
)
from domain.models.case import Case, CasePriority

logger = logging.getLogger(__name__)

# Automated dispatch threshold limit (in INR)
AUTOMATED_DISPATCH_MAX_AMOUNT = Decimal("25000.00")
SENIOR_APPROVAL_MIN_AMOUNT = Decimal("200000.00")
MAX_AUTOMATED_RECENCY_HOURS = 48


class ApprovalPolicyEngine:
    """
    Evaluates institutional escalation eligibility and assigns approval tiers.
    Enforces strict statutory compliance under BNSS 2023 and RBI guidelines:
    - AUTOMATED: Constrained STRICTLY to rapid Informational Fraud Alerts under ₹25k within 48h.
                 AUTOMATION NEVER EXECUTES A BINDING FREEZE OR LIEN.
    - INVESTIGATOR_APPROVED: Record summons under Section 94 BNSS, protective holds, or moderate amounts.
    - SENIOR_OFFICER: Formal statutory seizure under Section 106 BNSS, high exposure (>= ₹2L), or syndicate leads.
    """

    @classmethod
    def evaluate_eligibility(
        cls,
        case: Case,
        transaction: Optional[FinancialTransaction],
        target_bank: BankRegistry,
        escalation_role: str,
        is_mule_ring_suspect: bool = False,
        instruction_category: str = BankInstructionCategory.INFORMATIONAL_ALERT.value,
        beneficiary_bank_confidence: str = ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value
    ) -> Tuple[ApprovalTier, List[str], bool]:
        """
        Returns:
            (ApprovalTier, reasons_list, can_auto_dispatch)
        """
        reasons: List[str] = []
        can_auto = False

        amount_val = transaction.amount if transaction and transaction.amount is not None else (case.estimated_amount or case.estimated_loss_inr or 0.0)
        try:
            amount = Decimal(str(amount_val))
        except Exception:
            amount = Decimal("0.00")

        # Statutory Governance Guard 1: Formal Freezes & Seizures NEVER Automated
        # Section 106 / 107 BNSS mandates authorized police officer / IO authority.
        if instruction_category in [
            BankInstructionCategory.STATUTORY_FREEZE_ORDER.value,
            BankInstructionCategory.PROTECTIVE_HOLD_REQUEST.value
        ]:
            if amount >= SENIOR_APPROVAL_MIN_AMOUNT or is_mule_ring_suspect or case.priority == CasePriority.critical:
                tier = ApprovalTier.SENIOR_OFFICER
                reasons.append(
                    f"Statutory account freeze/seizure instruction under Section 106 BNSS (₹{amount:,.2f}) "
                    f"mandates Senior Officer / ACP authorization."
                )
            else:
                tier = ApprovalTier.INVESTIGATOR_APPROVED
                reasons.append(
                    f"Statutory account freeze/lien instruction under Section 106 BNSS mandates "
                    f"assigned duty investigator authorization."
                )
            return tier, reasons, False

        # Statutory Governance Guard 2: Section 94 BNSS Summons for Documents/KYC
        if instruction_category == BankInstructionCategory.RECORD_REQUEST_BNSS_94.value:
            tier = ApprovalTier.INVESTIGATOR_APPROVED
            reasons.append("Section 94 BNSS summons for bank records/KYC requires investigator review and signature.")
            return tier, reasons, False

        # Rule 1: High-Exposure / Senior LEA Approval Rule
        if amount >= SENIOR_APPROVAL_MIN_AMOUNT or case.priority == CasePriority.critical:
            tier = ApprovalTier.SENIOR_OFFICER
            reasons.append(f"Financial loss exposure (₹{amount:,.2f}) or critical priority mandates Senior Officer authorization.")
            return tier, reasons, False

        # Rule 2: Ongoing Syndicate / Mule Ring Trigger
        if is_mule_ring_suspect:
            tier = ApprovalTier.SENIOR_OFFICER
            reasons.append("Cross-institution graph correlation detected recurring mule accounts across independent cases.")
            return tier, reasons, False

        # Rule 3: Multi-Factor Automated Informational Alert Evaluation
        # Applicable strictly to informational alerts to halt fund layering during golden hour
        has_utr = bool(transaction and transaction.transaction_reference)
        has_bank_channel = bool(target_bank.is_active and target_bank.integration_type in ["SANDBOX_API", "DIRECT_API"])
        
        # Recency validation: must be within 48 hours to qualify for automated dispatch
        now_utc = datetime.now(timezone.utc)
        is_recent = True
        if transaction and transaction.transaction_time:
            is_recent = (now_utc - transaction.transaction_time) <= timedelta(hours=MAX_AUTOMATED_RECENCY_HOURS)
        elif case and case.created_at:
            is_recent = (now_utc - case.created_at) <= timedelta(hours=MAX_AUTOMATED_RECENCY_HOURS)

        if (
            instruction_category == BankInstructionCategory.INFORMATIONAL_ALERT.value
            and amount < AUTOMATED_DISPATCH_MAX_AMOUNT
            and has_utr
            and has_bank_channel
            and is_recent
            and not case.is_ongoing_fraud
        ):
            tier = ApprovalTier.AUTOMATED
            can_auto = True
            reasons.append(
                f"Automated Informational Alert approved: Amount (₹{amount:,.2f}) below threshold, "
                f"valid UTR ({transaction.transaction_reference}), fresh transaction (<=48h), and active {target_bank.bank_name} integration."
            )
            return tier, reasons, can_auto

        # Fallback Rule: Standard Duty Investigator Review
        reasons.append(
            f"Case queued for duty investigator review: Amount ₹{amount:,.2f}, role: {escalation_role}, instruction: {instruction_category}."
        )
        return ApprovalTier.INVESTIGATOR_APPROVED, reasons, False
