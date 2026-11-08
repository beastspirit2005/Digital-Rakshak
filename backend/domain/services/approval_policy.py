import logging
from typing import List, Tuple, Dict, Any, Optional
from domain.models.bank import ApprovalTier, BankRegistry, FinancialTransaction
from domain.models.case import Case, CasePriority

logger = logging.getLogger(__name__)

# Automated dispatch threshold limit (in INR)
AUTOMATED_DISPATCH_MAX_AMOUNT = 25000.0
SENIOR_APPROVAL_MIN_AMOUNT = 200000.0


class ApprovalPolicyEngine:
    """
    Evaluates institutional escalation eligibility and assigns approval tiers.
    Enforces hybrid policy gates:
    - AUTOMATED: Low-value, high-confidence, standard verified accounts
    - INVESTIGATOR_APPROVED: Moderate-value or unconfirmed VPA handles
    - SENIOR_OFFICER: High-value or ongoing syndicate threats
    """

    @classmethod
    def evaluate_eligibility(
        cls,
        case: Case,
        transaction: Optional[FinancialTransaction],
        target_bank: BankRegistry,
        escalation_role: str,
        is_mule_ring_suspect: bool = False
    ) -> Tuple[ApprovalTier, List[str], bool]:
        """
        Returns:
            (ApprovalTier, reasons_list, can_auto_dispatch)
        """
        reasons: List[str] = []
        tier = ApprovalTier.INVESTIGATOR_APPROVED
        can_auto = False

        amount = float(transaction.amount) if transaction and transaction.amount else float(case.estimated_amount or case.estimated_loss_inr or 0.0)

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

        # Rule 3: Automated Dispatch Evaluation
        has_utr = bool(transaction and transaction.transaction_reference)
        has_bank_channel = bool(target_bank.is_active and target_bank.integration_type in ["SANDBOX_API", "DIRECT_API"])
        
        if (
            amount < AUTOMATED_DISPATCH_MAX_AMOUNT
            and has_utr
            and has_bank_channel
            and not case.is_ongoing_fraud
        ):
            tier = ApprovalTier.AUTOMATED
            can_auto = True
            reasons.append(
                f"Automated Informational Alert approved: Amount (₹{amount:,.2f}) below threshold, "
                f"valid UTR ({transaction.transaction_reference}), and verified {target_bank.bank_name} integration."
            )
            return tier, reasons, can_auto

        # Fallback Rule: Standard Investigator Review
        reasons.append(
            f"Case queued for duty investigator review: Amount ₹{amount:,.2f}, role: {escalation_role}."
        )
        return ApprovalTier.INVESTIGATOR_APPROVED, reasons, False
