import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from domain.models.case import Case
from domain.models.bank import (
    BankRegistry,
    FinancialTransaction,
    BankEscalation,
    EscalationRole,
    EscalationStatus,
    ApprovalTier,
    BankInstructionCategory,
    ResolutionConfidenceType
)
from domain.services.transaction_extractor import (
    extract_transaction_intelligence,
    ExtractedTransactionIntelligence
)
from domain.services.bank_resolver import (
    BankResolverService,
    DualBankResolutionResult
)
from domain.services.approval_policy import ApprovalPolicyEngine
from domain.services.bank_integration_gateway import BankIntegrationGateway
from infrastructure.graph.neo4j_client import IntelligenceGraph

logger = logging.getLogger(__name__)


class BankRoutingEngine:
    """
    Coordinates multi-institution fraud alert generation, dual-bank routing,
    statutory approval evaluation under BNSS 2023, and automated/manual dispatch.
    """

    @classmethod
    async def process_and_route_case(
        cls,
        db: AsyncSession,
        case: Case,
        auto_dispatch_eligible: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point: Analyzes case narrative, creates/syncs FinancialTransaction,
        resolves dual banks, generates bank escalations, and executes automated dispatches.
        """
        # Step 1: Extract Transaction Intelligence from narrative
        intel: ExtractedTransactionIntelligence = extract_transaction_intelligence(case.scam_text)

        # Step 2: Ensure or create FinancialTransaction record with exact Decimal precision
        res_txn = await db.execute(
            select(FinancialTransaction).where(FinancialTransaction.case_id == case.id)
        )
        fin_txn = res_txn.scalar_one_or_none()

        reported_amt = Decimal(str(intel.amount)) if intel.amount else Decimal(str(case.estimated_amount or case.estimated_loss_inr or 0.0))

        if not fin_txn:
            fin_txn = FinancialTransaction(
                case_id=case.id,
                transaction_reference=intel.transaction_reference,
                amount=reported_amt,
                reported_loss_amount=reported_amt,
                currency="INR",
                payment_rail=intel.payment_rail,
                remitter_vpa=intel.remitter_vpa,
                remitter_account_masked=intel.remitter_account_masked,
                beneficiary_vpa=intel.beneficiary_vpa,
                beneficiary_account_masked=intel.beneficiary_account_masked,
                verification_status=intel.verification_status,
                raw_extraction=intel.model_dump()
            )
            db.add(fin_txn)
            await db.flush()
        else:
            # Update missing attributes if newly parsed
            if not fin_txn.transaction_reference and intel.transaction_reference:
                fin_txn.transaction_reference = intel.transaction_reference
            if not fin_txn.beneficiary_vpa and intel.beneficiary_vpa:
                fin_txn.beneficiary_vpa = intel.beneficiary_vpa
            if not fin_txn.beneficiary_account_masked and intel.beneficiary_account_masked:
                fin_txn.beneficiary_account_masked = intel.beneficiary_account_masked
            if not fin_txn.reported_loss_amount:
                fin_txn.reported_loss_amount = reported_amt
            await db.flush()

        # Step 3: Resolve Institutions (strictly distinguishing Candidate PSP vs Confirmed Bank)
        resolution: DualBankResolutionResult = await BankResolverService.resolve_institutions(db, intel)

        # Update IDs on fin_txn
        if resolution.remitter_institution.bank_id:
            fin_txn.remitter_bank_id = uuid.UUID(resolution.remitter_institution.bank_id)
        if resolution.beneficiary_institution.bank_id:
            fin_txn.beneficiary_bank_id = uuid.UUID(resolution.beneficiary_institution.bank_id)
            fin_txn.beneficiary_bank_confidence = resolution.beneficiary_institution.resolution_type
        await db.flush()

        # Step 4: Record into Neo4j Fraud Graph
        try:
            graph = IntelligenceGraph()
            await graph.record_case_financial_transaction(
                case_number=case.case_number,
                transaction_reference=fin_txn.transaction_reference,
                amount=float(fin_txn.amount),
                remitter_bank_code=resolution.remitter_institution.bank_code,
                beneficiary_bank_code=resolution.beneficiary_institution.bank_code,
                beneficiary_account=fin_txn.beneficiary_account_masked,
                beneficiary_vpa=fin_txn.beneficiary_vpa
            )
        except Exception as e:
            logger.warning(f"Non-blocking Neo4j graph recording warning: {e}")

        # Step 5: Check Graph Mule Ring Correlations
        is_mule_ring = False
        try:
            graph = IntelligenceGraph()
            correlations = await graph.get_cross_case_fraud_correlations(case.case_number)
            is_mule_ring = correlations.get("is_suspected_mule_ring", False)
        except Exception:
            pass

        created_escalations: List[Dict[str, Any]] = []

        # Step 6: Generate Dual-Bank Escalations with Statutory Alignment
        # A) Remitter Bank Escalation (Victim Bank — Payment Recall Notice)
        if resolution.remitter_institution.bank_id:
            esc_rem = await cls._generate_or_get_escalation(
                db=db,
                case=case,
                transaction=fin_txn,
                target_bank_id=uuid.UUID(resolution.remitter_institution.bank_id),
                role=EscalationRole.VICTIM_BANK.value,
                intel=intel,
                is_mule_ring=is_mule_ring,
                auto_dispatch=auto_dispatch_eligible,
                instruction_category=BankInstructionCategory.INFORMATIONAL_ALERT.value,
                statutory_basis="RBI_CUSTOMER_PROTECTION_2017",
                beneficiary_confidence=ResolutionConfidenceType.CONFIRMED_ACCOUNT_BANK.value
            )
            created_escalations.append(esc_rem)

        # B) Beneficiary Bank Escalation (Suspect Bank — Precautionary Lien / Record Request)
        if resolution.beneficiary_institution.bank_id:
            esc_ben = await cls._generate_or_get_escalation(
                db=db,
                case=case,
                transaction=fin_txn,
                target_bank_id=uuid.UUID(resolution.beneficiary_institution.bank_id),
                role=EscalationRole.BENEFICIARY_BANK.value,
                intel=intel,
                is_mule_ring=is_mule_ring,
                auto_dispatch=auto_dispatch_eligible,
                instruction_category=BankInstructionCategory.PROTECTIVE_HOLD_REQUEST.value,
                statutory_basis="BNSS_2023_SECTION_106_PROTECTIVE_HOLD",
                beneficiary_confidence=resolution.beneficiary_institution.resolution_type
            )
            created_escalations.append(esc_ben)

        await db.commit()

        return {
            "case_number": case.case_number,
            "routing_status": resolution.routing_status,
            "resolution_summary": resolution.resolution_summary,
            "overall_confidence": resolution.overall_confidence,
            "transaction_reference": fin_txn.transaction_reference,
            "amount": float(fin_txn.amount),
            "reported_loss_amount": float(fin_txn.reported_loss_amount or fin_txn.amount),
            "escalations_count": len(created_escalations),
            "escalations": created_escalations
        }

    @classmethod
    async def _generate_or_get_escalation(
        cls,
        db: AsyncSession,
        case: Case,
        transaction: FinancialTransaction,
        target_bank_id: uuid.UUID,
        role: str,
        intel: ExtractedTransactionIntelligence,
        is_mule_ring: bool,
        auto_dispatch: bool,
        instruction_category: str = BankInstructionCategory.INFORMATIONAL_ALERT.value,
        statutory_basis: str = "RBI_CUSTOMER_PROTECTION_2017",
        beneficiary_confidence: str = ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value
    ) -> Dict[str, Any]:
        """
        Creates a BankEscalation entity if not already generated, checks approval policy,
        and triggers automated API dispatch if eligible.
        """
        res = await db.execute(
            select(BankEscalation).where(
                BankEscalation.case_id == case.id,
                BankEscalation.target_bank_id == target_bank_id,
                BankEscalation.escalation_role == role
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            return {
                "id": str(existing.id),
                "alert_reference": existing.alert_reference,
                "role": existing.escalation_role,
                "instruction_category": existing.instruction_category,
                "statutory_basis": existing.statutory_basis,
                "status": existing.status,
                "approval_tier": existing.approval_tier,
                "target_bank_id": str(existing.target_bank_id)
            }

        res_bank = await db.execute(
            select(BankRegistry).where(BankRegistry.id == target_bank_id)
        )
        target_bank = res_bank.scalar_one_or_none()

        # Evaluate Statutory Approval Policy under BNSS 2023
        tier, reasons, can_auto = ApprovalPolicyEngine.evaluate_eligibility(
            case=case,
            transaction=transaction,
            target_bank=target_bank,
            escalation_role=role,
            is_mule_ring_suspect=is_mule_ring,
            instruction_category=instruction_category,
            beneficiary_bank_confidence=beneficiary_confidence
        )

        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        alert_ref = f"DR-ALERT-{today_str}-{uuid.uuid4().hex[:6].upper()}"
        # Logical idempotency key stays immutable for the lifetime of this instruction
        idempotency_key = f"IDEMP-{case.case_number}-{target_bank.bank_code}-{role}-{today_str}"

        # Standardized Statutory Alert Payload
        payload = {
            "alert_reference": alert_ref,
            "case_number": case.case_number,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "origin": "Digital Rakshak National Cyber Command & LEA Gateway",
            "statutory_basis": statutory_basis,
            "legal_citations": {
                "statutory_summons": "Section 94 Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023",
                "seizure_attachment": "Section 106/107 Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023",
                "electronic_evidence_admissibility": "Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023"
            },
            "instruction_category": instruction_category,
            "escalation_role": role,
            "beneficiary_confidence": beneficiary_confidence,
            "target_institution": {
                "bank_code": target_bank.bank_code,
                "bank_name": target_bank.bank_name,
                "ifsc_prefix": target_bank.ifsc_prefix
            },
            "transaction_details": {
                "reference_utr": transaction.transaction_reference,
                "amount_inr": str(transaction.amount),
                "payment_rail": transaction.payment_rail,
                "remitter_vpa": transaction.remitter_vpa,
                "remitter_account": transaction.remitter_account_masked,
                "beneficiary_vpa": transaction.beneficiary_vpa,
                "beneficiary_account": transaction.beneficiary_account_masked
            },
            "requested_action": (
                "Remitter security inspection, immediate recall assessment, and credential compromise audit."
                if role == EscalationRole.VICTIM_BANK.value
                else "Beneficiary surveillance, inward transaction debit lien check under Section 106 BNSS, and mule ring verification."
            ),
            "approval_evaluation": {
                "tier": tier.value,
                "reasons": reasons
            }
        }

        initial_status = EscalationStatus.READY.value if (can_auto and auto_dispatch) else EscalationStatus.PENDING_APPROVAL.value

        escalation = BankEscalation(
            case_id=case.id,
            transaction_id=transaction.id,
            alert_reference=alert_ref,
            target_bank_id=target_bank.id,
            escalation_role=role,
            instruction_category=instruction_category,
            statutory_basis=statutory_basis,
            beneficiary_bank_confidence=beneficiary_confidence,
            approval_tier=tier.value,
            status=initial_status,
            priority="HIGH" if is_mule_ring else "MEDIUM",
            alert_payload=payload,
            idempotency_key=idempotency_key
        )
        db.add(escalation)
        await db.flush()

        # If eligible for automated dispatch, fire immediately (STRICTLY constrained to Informational Alerts)
        dispatch_res = None
        if can_auto and auto_dispatch:
            try:
                dispatch_res = await BankIntegrationGateway.dispatch_escalation(
                    db=db,
                    escalation_id=escalation.id,
                    approver_user=None  # System automated
                )
            except Exception as e:
                logger.error(f"Error in automated dispatch for {alert_ref}: {e}")

        return {
            "id": str(escalation.id),
            "alert_reference": escalation.alert_reference,
            "role": escalation.escalation_role,
            "instruction_category": escalation.instruction_category,
            "statutory_basis": escalation.statutory_basis,
            "status": escalation.status,
            "approval_tier": escalation.approval_tier,
            "target_bank": target_bank.bank_name,
            "dispatch_result": dispatch_res
        }
