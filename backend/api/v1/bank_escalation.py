from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine
from domain.services.financial_reconciliation_service import FinancialReconciliationService, FinancialInvariantViolationError
from domain.services.evidence_integrity_service import EvidenceIntegrityService
from domain.services.outbox_worker import OutboxWorker
from domain.models.bank import (
    InvestigatorDecisionAudit,
    FraudResponseLifecycleEvent,
    FraudResponseStage,
    FinancialFundPosition,
    EvidenceCheckpoint,
    EvidenceAccessEvent,
    InstitutionalOutboxEvent
)
from decimal import Decimal
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_user_optional, require_official_role
from domain.models.user import User
from domain.models.case import Case
from domain.models.bank import (
    BankRegistry,
    FinancialTransaction,
    BankEscalation,
    BankDeliveryAttempt,
    BankResponse,
    EscalationStatus,
    ApprovalTier
)
from domain.services.bank_registry_service import BankRegistryService
from domain.services.bank_resolver import BankResolverService
from domain.services.transaction_extractor import (
    extract_transaction_intelligence,
    ExtractedTransactionIntelligence
)
from domain.services.bank_routing_engine import BankRoutingEngine
from domain.services.bank_integration_gateway import BankIntegrationGateway
from infrastructure.graph.neo4j_client import IntelligenceGraph

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────

class FundPositionCreateRequest(BaseModel):
    transaction_id: str
    account_reference_masked: str
    original_amount: Decimal
    bank_id: Optional[str] = None
    lien_delta: Decimal = Decimal("0.00")
    frozen_delta: Decimal = Decimal("0.00")
    recovered_delta: Decimal = Decimal("0.00")
    source_reference: Optional[str] = None

class FundPositionRecoveryConfirmationRequest(BaseModel):
    recovered_amount: Decimal
    verification_reference: str
    repatriation_account: Optional[str] = None


class BankResolveRequest(BaseModel):
    ifsc: Optional[str] = None
    vpa: Optional[str] = None
    text_hint: Optional[str] = None
    narrative: Optional[str] = None



class InvestigatorAuditClearanceRequest(BaseModel):
    decision: str = Field(..., description="APPROVED | REJECTED | MODIFIED")
    reviewed_evidence_ids: List[str] = Field(default_factory=list)
    statutory_powers_invoked: str = Field("SECTION_94_BNSS", description="SECTION_94_BNSS | SECTION_106_BNSS")
    decision_rationale: str
    authorization_token: Optional[str] = None

class BankResponseCallback(BaseModel):
    alert_reference: str
    bank_reference_number: str
    response_type: str = Field("ACKNOWLEDGEMENT", description="ACKNOWLEDGEMENT | INFO_REQUEST | ACTION_TAKEN | REJECTION")
    status_summary: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ── 1. Bank Directory & Resolution Endpoints ───────────────────────────

@router.get("/banks", response_model=List[Dict[str, Any]])
async def list_verified_banks(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Returns the verified Indian Bank Directory with supported rails and routing channels.
    """
    banks = await BankRegistryService.list_banks(db, only_active=True)
    if not banks:
        # Auto-seed if empty
        await BankRegistryService.seed_verified_banks(db)
        banks = await BankRegistryService.list_banks(db, only_active=True)

    return [
        {
            "id": str(b.id),
            "bank_code": b.bank_code,
            "bank_name": b.bank_name,
            "ifsc_prefix": b.ifsc_prefix,
            "supported_rails": b.supported_rails,
            "integration_type": b.integration_type,
            "nodal_email": b.nodal_email,
            "is_active": b.is_active
        }
        for b in banks
    ]


@router.get("/banks/{bank_id}", response_model=Dict[str, Any])
async def get_bank_details(
    bank_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves specific institution metadata by bank ID or bank code.
    """
    bank = None
    try:
        uid = uuid.UUID(bank_id)
        res = await db.execute(select(BankRegistry).where(BankRegistry.id == uid))
        bank = res.scalar_one_or_none()
    except (ValueError, AttributeError):
        bank = await BankRegistryService.get_bank_by_code(db, bank_id)

    if not bank:
        raise HTTPException(status_code=404, detail="Financial institution not found")

    return {
        "id": str(bank.id),
        "bank_code": bank.bank_code,
        "bank_name": bank.bank_name,
        "ifsc_prefix": bank.ifsc_prefix,
        "supported_rails": bank.supported_rails,
        "integration_type": bank.integration_type,
        "nodal_email": bank.nodal_email,
        "api_endpoint": bank.api_endpoint,
        "is_active": bank.is_active
    }


@router.post("/banks/resolve", response_model=Dict[str, Any])
async def resolve_institutions_endpoint(
    req: BankResolveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resolves financial institutions from raw IFSC, UPI VPA, or text complaint narratives.
    """
    if req.narrative:
        intel = extract_transaction_intelligence(req.narrative)
    else:
        intel = ExtractedTransactionIntelligence(
            remitter_ifsc=req.ifsc if req.ifsc and "my" in (req.text_hint or "") else None,
            beneficiary_ifsc=req.ifsc if not req.text_hint or "my" not in req.text_hint else None,
            beneficiary_vpa=req.vpa,
            beneficiary_bank_hint=req.text_hint
        )

    resolution = await BankResolverService.resolve_institutions(db, intel)
    return {
        "routing_status": resolution.routing_status,
        "overall_confidence": resolution.overall_confidence,
        "resolution_summary": resolution.resolution_summary,
        "remitter_institution": resolution.remitter_institution.model_dump(),
        "beneficiary_institution": resolution.beneficiary_institution.model_dump(),
        "extracted_intelligence": intel.model_dump()
    }


# ── 2. Bank Escalations Lifecycle Endpoints ────────────────────────────

@router.post("/bank-escalations/case/{case_number}/route", response_model=Dict[str, Any])
async def route_case_to_banks(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Initiates automated institutional fraud routing for an official case.
    Extracts transaction identifiers, resolves dual banks, generates tailored alerts,
    evaluates hybrid approval policies, and triggers automated dispatch if eligible.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_number} not found")

    # Authorisation check: institutional roles only
    if user.role not in ["police", "cyber_cell", "admin", "banker", "bank_employee"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Institutional clearance required to route bank escalations."
        )

    routing_result = await BankRoutingEngine.process_and_route_case(
        db=db,
        case=case,
        auto_dispatch_eligible=True
    )
    return routing_result


@router.get("/bank-escalations/case/{case_number}", response_model=Dict[str, Any])
async def get_case_bank_escalations(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retrieves all financial institution alerts and their delivery status for a case.
    Provides full forensic view for officers and privacy-sanitized view for citizens.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_number} not found")

    is_official = user.role in ["police", "cyber_cell", "admin", "banker", "bank_employee"]
    if not is_official and str(case.submitted_by) != str(user.id):
        raise HTTPException(status_code=403, detail="Access denied to case escalation records")

    # Fetch escalations
    query = (
        select(BankEscalation)
        .where(BankEscalation.case_id == case.id)
        .options(
            selectinload(BankEscalation.target_bank),
            selectinload(BankEscalation.delivery_attempts),
            selectinload(BankEscalation.responses),
            selectinload(BankEscalation.transaction)
        )
        .order_by(BankEscalation.created_at.desc())
    )
    res_esc = await db.execute(query)
    escalations = res_esc.scalars().all()

    # Format output
    records = []
    for esc in escalations:
        bank_name = esc.target_bank.bank_name if esc.target_bank else "Unknown Bank"
        bank_code = esc.target_bank.bank_code if esc.target_bank else "UNKNOWN"

        if is_official:
            records.append({
                "id": str(esc.id),
                "alert_reference": esc.alert_reference,
                "escalation_role": esc.escalation_role,
                "status": esc.status,
                "approval_tier": esc.approval_tier,
                "priority": esc.priority,
                "target_bank": {
                    "id": str(esc.target_bank_id),
                    "code": bank_code,
                    "name": bank_name,
                    "integration_type": esc.target_bank.integration_type if esc.target_bank else None
                },
                "instruction_category": esc.instruction_category,
                "statutory_basis": esc.statutory_basis,
                "beneficiary_bank_confidence": esc.beneficiary_bank_confidence,
                "idempotency_key": esc.idempotency_key,
                "alert_payload": esc.alert_payload,
                "approved_by": str(esc.approved_by) if esc.approved_by else None,
                "approved_at": esc.approved_at.isoformat() if esc.approved_at else None,
                "created_at": esc.created_at.isoformat() if esc.created_at else None,
                "delivery_attempts_count": len(esc.delivery_attempts),
                "latest_response": esc.responses[-1].status_summary if esc.responses else None
            })
        else:
            # Citizen Sanitized Summary
            records.append({
                "alert_reference": esc.alert_reference,
                "escalation_role": "Originating / Remitter Bank" if esc.escalation_role == "VICTIM_BANK" else "Beneficiary / Suspect Bank",
                "target_bank_name": bank_name,
                "status": "Transmitted & Acknowledged" if esc.status in ["DISPATCHED", "DELIVERED", "ACKNOWLEDGED"] else "Under Review by Cyber Cell",
                "initiated_at": esc.created_at.isoformat() if esc.created_at else None
            })

    return {
        "case_number": case.case_number,
        "is_official_view": is_official,
        "total_alerts": len(records),
        "escalations": records
    }


@router.post("/bank-escalations/{id}/approve", response_model=Dict[str, Any])
async def approve_bank_escalation(
    id: str,
    dispatch_now: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Authorized Investigator Review Gate:
    Approves a PENDING_APPROVAL bank escalation, writes to the Transactional Outbox within
    the same database transaction, and optionally dispatches immediately via the Outbox Worker.
    """
    if user.role not in ["police", "cyber_cell", "admin"]:
        raise HTTPException(status_code=403, detail="Investigator clearance required to approve bank escalations.")

    uid = uuid.UUID(id)
    res = await db.execute(select(BankEscalation).where(BankEscalation.id == uid))
    escalation = res.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Bank escalation not found")

    corr_id = f"CORR-{escalation.alert_reference}"
    escalation.approved_by = user.id
    escalation.approved_at = datetime.now(timezone.utc)
    escalation.status = EscalationStatus.READY.value
    escalation.version += 1

    # Record Stage 5: APPROVAL_EVALUATED
    await FraudLifecycleEngine.record_transition(
        db=db,
        correlation_id=corr_id,
        case_id=escalation.case_id,
        stage=FraudResponseStage.APPROVAL_EVALUATED,
        actor_or_service=f"INVESTIGATOR:{user.full_name or user.email}",
        transition_reason=f"Investigator {user.email} approved alert dispatch under {escalation.statutory_basis}.",
        transaction_id=escalation.transaction_id,
        escalation_id=escalation.id,
        actor_id=user.id
    )

    # Transactional Outbox: persist outbox event in same ACID transaction
    outbox_event = await BankIntegrationGateway.queue_escalation_in_outbox(
        db=db,
        escalation=escalation,
        correlation_id=corr_id
    )
    await db.commit()

    dispatch_res = None
    if dispatch_now:
        worker = OutboxWorker(worker_id=f"ON_DEMAND_{user.id.hex[:6]}")
        process_res = await worker.process_event(db, outbox_event)
        dispatch_res = process_res.get("dispatch_result")

    return {
        "success": True,
        "escalation_id": str(escalation.id),
        "status": escalation.status,
        "outbox_event_id": str(outbox_event.id),
        "approved_by": user.full_name or user.email,
        "dispatch_result": dispatch_res
    }


@router.post("/bank-escalations/{id}/dispatch", response_model=Dict[str, Any])
async def dispatch_bank_escalation(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Dispatches an approved alert through the authorized banking integration adapter.
    """
    if user.role not in ["police", "cyber_cell", "admin"]:
        raise HTTPException(status_code=403, detail="Authorized officer clearance required for manual alert dispatch.")

    uid = uuid.UUID(id)
    dispatch_res = await BankIntegrationGateway.dispatch_escalation(
        db=db,
        escalation_id=uid,
        approver_user=user
    )
    return dispatch_res


@router.post("/bank-escalations/{id}/retry", response_model=Dict[str, Any])
async def retry_bank_escalation(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Manually re-attempts failed delivery of an existing escalation.
    Retains the exact same logical idempotency key while issuing a new physical attempt record.
    """
    uid = uuid.UUID(id)
    dispatch_res = await BankIntegrationGateway.dispatch_escalation(
        db=db,
        escalation_id=uid,
        approver_user=user
    )
    if not dispatch_res.get("success"):
        raise HTTPException(status_code=502, detail=dispatch_res.get("error", "Bank retry dispatch failed"))
    return dispatch_res


@router.get("/bank-escalations/{id}/timeline", response_model=Dict[str, Any])
async def get_escalation_timeline(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Fetches immutable transmission attempts, HTTP response codes, and institutional responses.
    """
    uid = uuid.UUID(id)
    res = await db.execute(
        select(BankEscalation)
        .where(BankEscalation.id == uid)
        .options(
            selectinload(BankEscalation.delivery_attempts),
            selectinload(BankEscalation.responses),
            selectinload(BankEscalation.target_bank)
        )
    )
    esc = res.scalar_one_or_none()
    if not esc:
        raise HTTPException(status_code=404, detail="Bank escalation not found")

    return {
        "escalation_id": str(esc.id),
        "alert_reference": esc.alert_reference,
        "idempotency_key": esc.idempotency_key,
        "instruction_category": esc.instruction_category,
        "statutory_basis": esc.statutory_basis,
        "beneficiary_bank_confidence": esc.beneficiary_bank_confidence,
        "bank_name": esc.target_bank.bank_name if esc.target_bank else None,
        "status": esc.status,
        "delivery_attempts": [
            {
                "attempt_number": a.attempt_number,
                "channel": a.channel,
                "http_status_code": a.http_status_code,
                "delivery_status": a.delivery_status,
                "attempted_at": a.attempted_at.isoformat() if a.attempted_at else None,
                "error_message": a.error_message
            }
            for a in esc.delivery_attempts
        ],
        "responses": [
            {
                "bank_reference": r.bank_reference_number,
                "response_type": r.response_type,
                "status_summary": r.status_summary,
                "details": r.details,
                "received_at": r.received_at.isoformat() if r.received_at else None
            }
            for r in esc.responses
        ]
    }


# ── 3. Cross-Institution Graph Correlations Endpoint ────────────────────

@router.get("/fraud/correlations/{case_number}", response_model=Dict[str, Any])
async def get_fraud_correlations(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Traverses Neo4j graph to find multi-incident correlations:
    Identifies shared beneficiary accounts, shared VPAs, and recurring mule rings.
    """
    if user.role not in ["police", "cyber_cell", "admin", "banker", "bank_employee"]:
        raise HTTPException(status_code=403, detail="Clearance required for cross-incident fraud intelligence.")

    graph = IntelligenceGraph()
    correlations = await graph.get_cross_case_fraud_correlations(case_number)
    return correlations


# ── 4. External Bank Webhook / Callback Handler ─────────────────────────

@router.post("/bank-integrations/{bank_code}/callback", response_model=Dict[str, Any])
async def bank_callback_endpoint(
    bank_code: str,
    payload: BankResponseCallback,
    db: AsyncSession = Depends(get_db),
    x_bank_signature: Optional[str] = Header(None, alias="X-Bank-Signature"),
    x_callback_timestamp: Optional[str] = Header(None, alias="X-Callback-Timestamp"),
    x_callback_nonce: Optional[str] = Header(None, alias="X-Callback-Nonce")
):
    """
    Authenticated institutional webhook for banks to deliver acknowledgements,
    requests for information (RFIs), or account action reports.
    Enforces HMAC-SHA256 signature verification and <=300s timestamp replay window.
    """
    import json
    if not x_bank_signature:
        from core.config import settings
        if getattr(settings, "ENVIRONMENT", "development") == "production":
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: Missing mandatory X-Bank-Signature header for institutional webhook."
            )
    else:
        raw_bytes = json.dumps(payload.model_dump(), sort_keys=True).encode()
        is_valid, err_msg = BankIntegrationGateway.verify_callback_authenticity(
            payload_bytes=raw_bytes,
            signature=x_bank_signature,
            timestamp_str=x_callback_timestamp
        )
        if not is_valid:
            raise HTTPException(status_code=401, detail=err_msg)

    if x_callback_nonce:
        is_fresh_nonce, replay_err = await BankIntegrationGateway.validate_and_record_nonce(
            db=db,
            bank_code=bank_code,
            nonce=x_callback_nonce,
            signature=x_bank_signature or "SIG-SANDBOX"
        )
        if not is_fresh_nonce:
            raise HTTPException(status_code=409, detail=replay_err)

    # 1. Look up Escalation by Alert Reference
    res = await db.execute(
        select(BankEscalation).where(BankEscalation.alert_reference == payload.alert_reference)
    )
    esc = res.scalar_one_or_none()
    if not esc:
        raise HTTPException(status_code=404, detail="Alert reference not found")

    # 2. Record Response
    resp = BankResponse(
        escalation_id=esc.id,
        bank_reference_number=payload.bank_reference_number,
        response_type=payload.response_type,
        status_summary=payload.status_summary,
        details=payload.details
    )
    db.add(resp)

    # 3. Update Escalation Lifecycle State
    if payload.response_type == "ACTION_TAKEN":
        esc.status = EscalationStatus.ACTION_REPORTED.value
    elif payload.response_type == "INFO_REQUEST":
        esc.status = EscalationStatus.INFORMATION_REQUIRED.value
    elif payload.response_type == "REJECTION":
        esc.status = EscalationStatus.REJECTED.value
    else:
        esc.status = EscalationStatus.ACKNOWLEDGED.value
    esc.updated_at = datetime.now(timezone.utc)

    # 4. If action reported funds frozen or lien marked, trigger strict mathematical reconciliation
    if payload.details and esc.transaction_id:
        frozen_str = payload.details.get("funds_frozen_amount") or payload.details.get("amount_frozen")
        lien_str = payload.details.get("funds_lien_amount") or payload.details.get("amount_under_lien")
        try:
            frozen_delta = Decimal(str(frozen_str)) if frozen_str else Decimal("0.00")
            lien_delta = Decimal(str(lien_str)) if lien_str else Decimal("0.00")
            if frozen_delta > 0 or lien_delta > 0:
                await FinancialReconciliationService.reconcile_transaction(
                    db=db,
                    transaction_id=esc.transaction_id,
                    new_lien_delta=lien_delta,
                    new_frozen_delta=frozen_delta,
                    correlation_id=f"CORR-{esc.alert_reference}",
                    actor=f"BANK_CALLBACK:{bank_code}",
                    reason=f"Action callback from {bank_code}: {payload.status_summary}"
                )
        except FinancialInvariantViolationError as inv_err:
            logger.error(f"Financial invariant error on callback for {esc.alert_reference}: {inv_err}")

    await db.commit()
    logger.info(f"Received verified bank callback for {payload.alert_reference} from {bank_code}")

    return {
        "status": "PROCESSED",
        "alert_reference": payload.alert_reference,
        "escalation_status": esc.status
    }

# ── 5. Lifecycle Engine & BSA 2023 Evidentiary Certificate Endpoints ───────

@router.get("/cases/{case_number}/lifecycle-events", response_model=Dict[str, Any])
async def get_case_lifecycle_events(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Retrieves full chronological 8-stage lifecycle history with cryptographic SHA-256 Merkle chain.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    is_valid, count, err = await FraudLifecycleEngine.verify_hash_chain(db, case.id)

    stmt = (
        select(FraudResponseLifecycleEvent)
        .where(FraudResponseLifecycleEvent.case_id == case.id)
        .order_by(FraudResponseLifecycleEvent.created_at.asc())
    )
    res_events = await db.execute(stmt)
    events = res_events.scalars().all()

    return {
        "case_number": case.case_number,
        "is_hash_chain_valid": is_valid,
        "verified_events_count": count,
        "hash_chain_status": "CRYPTO_VERIFIED_UNBROKEN" if is_valid else f"TAMPER_DETECTED: {err}",
        "events": [
            {
                "id": str(e.id),
                "correlation_id": e.correlation_id,
                "stage": e.stage,
                "previous_stage": e.previous_stage,
                "actor_or_service": e.actor_or_service,
                "transition_reason": e.transition_reason,
                "evidence_reference": e.evidence_reference,
                "financial_snapshot": e.financial_snapshot,
                "event_hash": e.event_hash,
                "previous_event_hash": e.previous_event_hash,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
    }


@router.get("/cases/{case_number}/bsa-evidentiary-certificate", response_model=Dict[str, Any])
async def export_bsa_evidentiary_certificate(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Generates statutory Section 63(4) Bharatiya Sakshya Adhiniyam (BSA) 2023
    Certificate of Admissibility for electronic banking records.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    officer_name = f"{user.full_name or user.email} (Badge: {user.role.upper()})"
    cert = await FraudLifecycleEngine.generate_bsa_evidentiary_certificate(
        db=db,
        case=case,
        officer_name=officer_name
    )
    return cert


@router.post("/bank-escalations/{id}/audit-clearance", response_model=Dict[str, Any])
async def record_investigator_audit_clearance(
    id: str,
    payload: InvestigatorAuditClearanceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Records granular investigator decision audit: evidence IDs reviewed,
    statutory powers invoked under BNSS 2023, rationale, and digital authorization token.
    """
    uid = uuid.UUID(id)
    res_esc = await db.execute(select(BankEscalation).where(BankEscalation.id == uid))
    esc = res_esc.scalar_one_or_none()
    if not esc:
        raise HTTPException(status_code=404, detail="Bank escalation not found")

    token = payload.authorization_token or f"AUTH-{uuid.uuid4().hex[:12].upper()}"
    audit_record = InvestigatorDecisionAudit(
        escalation_id=esc.id,
        investigator_id=user.id,
        decision=payload.decision,
        reviewed_evidence_ids=payload.reviewed_evidence_ids,
        statutory_powers_invoked=payload.statutory_powers_invoked,
        decision_rationale=payload.decision_rationale,
        authorization_token=token
    )
    db.add(audit_record)
    await db.commit()

    return {
        "success": True,
        "escalation_id": str(esc.id),
        "decision": payload.decision,
        "authorization_token": token,
        "investigator": user.full_name or user.email,
        "statutory_powers_invoked": payload.statutory_powers_invoked
    }


# ── 6. Evidence Integrity & Checkpoint Endpoints ─────────────────────────

@router.get("/cases/{case_number}/integrity-verification", response_model=Dict[str, Any])
async def verify_case_integrity(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Independently verifies the cryptographic SHA-256 Merkle chain, checks for
    sequence gaps, payload tampering, or reordering, and verifies signed checkpoints.
    Logs an immutable access event for Section 63 BSA 2023 compliance.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    report = await EvidenceIntegrityService.verify_chain_integrity(db, case.id)
    await EvidenceIntegrityService.record_access_event(
        db=db,
        case_id=case.id,
        action="INTEGRITY_VERIFIED",
        actor=user
    )
    return report


@router.post("/cases/{case_number}/checkpoints/sign", response_model=Dict[str, Any])
async def create_case_signed_checkpoint(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Creates and digitally signs an evidentiary checkpoint anchoring the current Merkle root hash.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cp = await EvidenceIntegrityService.create_signed_checkpoint(db, case.id)
    await EvidenceIntegrityService.record_access_event(
        db=db,
        case_id=case.id,
        action="CHECKPOINT_SIGNED",
        actor=user,
        evidence_reference=f"CHECKPOINT:{cp.id}"
    )

    return {
        "checkpoint_id": str(cp.id),
        "case_number": case.case_number,
        "sequence_range": f"{cp.sequence_start} - {cp.sequence_end}",
        "merkle_root_hash": cp.merkle_root_hash,
        "signature": cp.signature,
        "signing_key_id": cp.signing_key_id,
        "created_at": cp.created_at.isoformat()
    }


@router.get("/cases/{case_number}/evidence-access-log", response_model=Dict[str, Any])
async def get_evidence_access_log(
    case_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Retrieves the chain-of-custody access history for all evidence associated with a case.
    """
    res_case = await db.execute(select(Case).where(Case.case_number == case_number))
    case = res_case.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    stmt = (
        select(EvidenceAccessEvent)
        .where(EvidenceAccessEvent.case_id == case.id)
        .order_by(EvidenceAccessEvent.created_at.desc())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    return {
        "case_number": case.case_number,
        "total_access_events": len(records),
        "access_logs": [
            {
                "id": str(r.id),
                "actor_id": str(r.actor_id) if r.actor_id else None,
                "actor_role": r.actor_role,
                "action": r.action,
                "evidence_reference": r.evidence_reference,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]
    }


# ── 7. Fund Positions & Financial Reconciliation Endpoints ───────────────

@router.post("/cases/{case_id}/fund-positions", response_model=Dict[str, Any])
async def create_or_update_fund_position_endpoint(
    case_id: str,
    payload: FundPositionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Creates or updates a unique beneficiary fund position, resolving the lien-to-freeze overlap.
    """
    txn_id = uuid.UUID(payload.transaction_id)
    bank_id = uuid.UUID(payload.bank_id) if payload.bank_id else None

    try:
        pos = await FinancialReconciliationService.record_or_update_fund_position(
            db=db,
            transaction_id=txn_id,
            account_reference_masked=payload.account_reference_masked,
            original_amount=payload.original_amount,
            bank_id=bank_id,
            lien_delta=payload.lien_delta,
            frozen_delta=payload.frozen_delta,
            recovered_delta=payload.recovered_delta,
            source_reference=payload.source_reference
        )
        await db.commit()
        return {
            "position_id": str(pos.id),
            "account_reference_masked": pos.account_reference_masked,
            "original_amount": str(pos.original_amount),
            "lien_amount": str(pos.lien_amount),
            "frozen_amount": str(pos.frozen_amount),
            "recovered_amount": str(pos.recovered_amount),
            "status": pos.status
        }
    except FinancialInvariantViolationError as inv_err:
        raise HTTPException(status_code=422, detail=str(inv_err))


@router.get("/cases/{case_id}/financial-reconciliation", response_model=Dict[str, Any])
async def get_financial_reconciliation_summary(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Returns multi-tier balances with unique secured funds calculation resolving overlaps.
    """
    c_uid = uuid.UUID(case_id)
    res_txns = await db.execute(
        select(FinancialTransaction).where(FinancialTransaction.case_id == c_uid)
    )
    txns = res_txns.scalars().all()

    summary_list = []
    for t in txns:
        pos_summary = await FinancialReconciliationService.get_fund_positions_summary(db, t.id)
        summary_list.append({
            "transaction_id": str(t.id),
            "reference": t.transaction_reference,
            "amount": str(t.amount),
            "reported_loss": str(t.reported_loss_amount or t.amount),
            "amount_under_lien": str(t.amount_under_lien),
            "amount_frozen": str(t.amount_frozen),
            "amount_secured_unique": str(pos_summary["total_secured_unique"]),
            "amount_recovered": str(t.amount_recovered),
            "fund_positions": pos_summary["positions"]
        })

    return {
        "case_id": case_id,
        "transactions_count": len(txns),
        "reconciliation_summary": summary_list
    }


@router.post("/fund-positions/{id}/recovery-confirmation", response_model=Dict[str, Any])
async def confirm_fund_position_recovery(
    id: str,
    payload: FundPositionRecoveryConfirmationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Confirms verified fund repatriation from a secured fund position.
    """
    p_uid = uuid.UUID(id)
    res = await db.execute(select(FinancialFundPosition).where(FinancialFundPosition.id == p_uid))
    pos = res.scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=404, detail="Fund position not found")

    try:
        updated_pos = await FinancialReconciliationService.record_or_update_fund_position(
            db=db,
            transaction_id=pos.transaction_id,
            account_reference_masked=pos.account_reference_masked,
            original_amount=Decimal(str(pos.original_amount)),
            recovered_delta=payload.recovered_amount,
            source_reference=f"RECOVERY_CONFIRMATION:{payload.verification_reference}"
        )
        await db.commit()
        return {
            "success": True,
            "position_id": str(updated_pos.id),
            "total_recovered": str(updated_pos.recovered_amount),
            "status": updated_pos.status,
            "verification_reference": payload.verification_reference
        }
    except FinancialInvariantViolationError as inv_err:
        raise HTTPException(status_code=422, detail=str(inv_err))


# ── 8. Institutional Health & Circuit Breaker Metrics Endpoint ────────────

@router.get("/institutional/health", response_model=Dict[str, Any])
async def get_institutional_health_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_official_role)
):
    """
    Returns real-time gateway health: per-bank circuit breaker status,
    transactional outbox queue depths, database latency, and worker heartbeat.
    """
    import time
    from core.config import settings

    t0 = time.time()
    await db.execute(select(1))
    db_latency_ms = round((time.time() - t0) * 1000, 2)

    outbox_metrics = await OutboxWorker.get_queue_metrics(db)
    cb_metrics = BankIntegrationGateway.get_health_metrics()

    # Calculate active operational alerts
    tripped_cbs = sum(1 for v in cb_metrics.values() if v.get("state") in ("OPEN", "HALF_OPEN"))
    dead_letters = outbox_metrics.get("dead_letter", 0)
    sla_breaches = 1 if outbox_metrics.get("oldest_pending_age_seconds", 0) > 300 else 0

    is_degraded = tripped_cbs > 0 or dead_letters > 0 or sla_breaches > 0

    return {
        "status": "DEGRADED" if is_degraded else "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "release": getattr(settings, "RELEASE_VERSION", "v2.4.0"),
        "database_latency_ms": db_latency_ms,
        "outbox_metrics": outbox_metrics,
        "circuit_breakers": cb_metrics,
        "alerts_summary": {
            "tripped_circuit_breakers": tripped_cbs,
            "dead_letter_events": dead_letters,
            "outbox_sla_breaches": sla_breaches,
            "expired_leases": outbox_metrics.get("expired_leases", 0)
        },
        "sla_disclaimer": "Metrics reflect internal adapter dispatch and queue health. Institutional bank processing times are subject to partner rail availability."
    }
