import logging
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from domain.models.bank import BankRegistry, TransactionVerificationStatus, ResolutionConfidenceType
from domain.services.bank_registry_service import BankRegistryService
from domain.services.transaction_extractor import ExtractedTransactionIntelligence

logger = logging.getLogger(__name__)


class InstitutionResolution(BaseModel):
    bank_id: Optional[str] = None
    bank_code: Optional[str] = None
    bank_name: Optional[str] = None
    resolution_source: str = Field("UNRESOLVED", description="IFSC | VPA_HANDLE | NAME_HINT | UNRESOLVED")
    resolution_type: str = Field(
        ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value,
        description="CONFIRMED_ACCOUNT_BANK | CANDIDATE_PSP_ROUTING"
    )
    is_account_bank_confirmed: bool = False
    resolution_status: str = Field(TransactionVerificationStatus.UNRESOLVED.value)
    confidence: float = 0.0
    candidate_psp_notes: Optional[str] = None


class DualBankResolutionResult(BaseModel):
    routing_status: str = Field("UNRESOLVED", description="BOTH_RESOLVED | PARTIALLY_RESOLVED | UNRESOLVED")
    remitter_institution: InstitutionResolution = Field(default_factory=InstitutionResolution)
    beneficiary_institution: InstitutionResolution = Field(default_factory=InstitutionResolution)
    overall_confidence: float = 0.0
    resolution_summary: str = ""


class BankResolverService:
    """
    Resolves financial institutions (both victim remitter bank and suspect beneficiary bank)
    using multi-layered metadata matching (IFSC prefix, UPI VPA handle, bank name hints).
    Strictly distinguishes candidate PSP routing arrangements from confirmed account-holding banks.
    """

    @classmethod
    async def resolve_institutions(
        cls,
        db: AsyncSession,
        intelligence: ExtractedTransactionIntelligence
    ) -> DualBankResolutionResult:
        """
        Executes cascade resolution for remitter and beneficiary financial institutions.
        """
        # Ensure bank directory is seeded
        await BankRegistryService.seed_verified_banks(db)

        # 1. Resolve Remitter / Victim Bank
        remitter_res = await cls._resolve_single_side(
            db,
            ifsc=intelligence.remitter_ifsc,
            vpa=intelligence.remitter_vpa,
            name_hint=intelligence.remitter_bank_hint
        )

        # 2. Resolve Beneficiary / Suspect Bank
        beneficiary_res = await cls._resolve_single_side(
            db,
            ifsc=intelligence.beneficiary_ifsc,
            vpa=intelligence.beneficiary_vpa,
            name_hint=intelligence.beneficiary_bank_hint
        )

        # Determine overall routing status
        rem_ok = remitter_res.bank_id is not None
        ben_ok = beneficiary_res.bank_id is not None

        if rem_ok and ben_ok:
            routing_status = "BOTH_RESOLVED"
            overall_conf = round((remitter_res.confidence + beneficiary_res.confidence) / 2.0, 2)
            ben_qualifier = "Confirmed" if beneficiary_res.is_account_bank_confirmed else "Candidate PSP"
            summary = (
                f"Both institutions resolved: Victim={remitter_res.bank_name}, "
                f"Beneficiary={beneficiary_res.bank_name} ({ben_qualifier})."
            )
        elif rem_ok or ben_ok:
            routing_status = "PARTIALLY_RESOLVED"
            active_conf = remitter_res.confidence if rem_ok else beneficiary_res.confidence
            overall_conf = round(active_conf * 0.75, 2)
            resolved_party = f"Victim Bank ({remitter_res.bank_name})" if rem_ok else f"Beneficiary Bank ({beneficiary_res.bank_name})"
            summary = f"Partial resolution: Only {resolved_party} identified. Investigation details needed for counterpart."
        else:
            routing_status = "UNRESOLVED"
            overall_conf = 0.1
            summary = "Insufficient transaction metadata to identify involved financial institutions."

        return DualBankResolutionResult(
            routing_status=routing_status,
            remitter_institution=remitter_res,
            beneficiary_institution=beneficiary_res,
            overall_confidence=overall_conf,
            resolution_summary=summary
        )

    @classmethod
    async def _resolve_single_side(
        cls,
        db: AsyncSession,
        ifsc: Optional[str] = None,
        vpa: Optional[str] = None,
        name_hint: Optional[str] = None
    ) -> InstitutionResolution:
        # Step A: Exact IFSC lookup (Highest confidence 0.95 — Confirmed Account Bank)
        if ifsc:
            bank = await BankRegistryService.resolve_bank_from_ifsc(db, ifsc)
            if bank:
                return InstitutionResolution(
                    bank_id=str(bank.id),
                    bank_code=bank.bank_code,
                    bank_name=bank.bank_name,
                    resolution_source="IFSC",
                    resolution_type=ResolutionConfidenceType.CONFIRMED_ACCOUNT_BANK.value,
                    is_account_bank_confirmed=True,
                    resolution_status=TransactionVerificationStatus.VERIFIED.value,
                    confidence=0.95,
                    candidate_psp_notes="Confirmed via authoritative IFSC code."
                )

        # Step B: UPI VPA Handle lookup (Candidate PSP Routing Arrangement)
        # Suffix like @okhdfcbank indicates PSP/acquiring routing, NOT universally confirmed account bank.
        if vpa:
            bank = await BankRegistryService.resolve_bank_from_vpa(db, vpa)
            if bank:
                return InstitutionResolution(
                    bank_id=str(bank.id),
                    bank_code=bank.bank_code,
                    bank_name=bank.bank_name,
                    resolution_source="VPA_HANDLE",
                    resolution_type=ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value,
                    is_account_bank_confirmed=False,
                    resolution_status=TransactionVerificationStatus.RESOLVED_INFERRED.value,
                    confidence=0.50,
                    candidate_psp_notes="VPA handle identifies PSP acquiring bank; beneficiary account-holding bank remains candidate until confirmed by statement or NPCI response."
                )

        # Step C: Bank Name Keyword Hint lookup (Candidate Bank from narrative)
        if name_hint:
            bank = await BankRegistryService.get_bank_by_code(db, name_hint)
            if bank:
                return InstitutionResolution(
                    bank_id=str(bank.id),
                    bank_code=bank.bank_code,
                    bank_name=bank.bank_name,
                    resolution_source="NAME_HINT",
                    resolution_type=ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value,
                    is_account_bank_confirmed=False,
                    resolution_status=TransactionVerificationStatus.RESOLVED_INFERRED.value,
                    confidence=0.55,
                    candidate_psp_notes="Resolved from citizen text narrative keywords; unconfirmed."
                )

        return InstitutionResolution(
            bank_id=None,
            bank_code=None,
            bank_name=None,
            resolution_source="UNRESOLVED",
            resolution_type=ResolutionConfidenceType.CANDIDATE_PSP_ROUTING.value,
            is_account_bank_confirmed=False,
            resolution_status=TransactionVerificationStatus.UNRESOLVED.value,
            confidence=0.0,
            candidate_psp_notes=None
        )
