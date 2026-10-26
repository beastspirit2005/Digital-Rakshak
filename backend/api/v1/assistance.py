import uuid
import secrets
import datetime
from datetime import timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from infrastructure.db.session import get_db
from api.deps import get_current_user, require_pro_user
from fastapi.responses import Response
from infrastructure.pdf.dossier_pdf import generate_fir_dossier_pdf
from domain.models.user import User
from domain.models.case import Case, CaseStatus, CasePriority
from domain.models.case_event import CaseEvent
from domain.models.audit_event import AuditEvent
from domain.services.urgency_engine import UrgencyEngine

router = APIRouter(prefix="/assistance-requests", tags=["assistance-requests"])

class AssistanceSubmissionRequest(BaseModel):
    incident_type: str = Field(..., description="e.g. digital_arrest, banking_fraud, upi_fraud, phishing, extortion")
    narrative: str = Field(..., min_length=10, description="Detailed account of what occurred")
    is_ongoing_fraud: bool = Field(False, description="Whether the threat or financial drain is currently ongoing")
    hours_since_incident: float = Field(0.0, ge=0.0, description="Approximate hours since the scam occurred")
    estimated_loss_inr: Optional[float] = Field(0.0, ge=0.0, description="Estimated financial loss in INR")
    has_compromised_credentials: bool = Field(False, description="Whether passwords, OTPs, or PINs were entered")
    victim_phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

class AssistanceResponse(BaseModel):
    reference: str
    case_id: str
    urgency_level: str
    status: str
    incident_type: str
    created_at: str
    emergency_guidance: List[Dict[str, Any]]
    reasons: List[str]

def generate_assistance_reference() -> str:
    year = datetime.datetime.now(timezone.utc).year
    # 6-character cryptographically safe random hex (16.7M combinations per year)
    rand_code = secrets.token_hex(3).upper()
    return f"DR-{year}-{rand_code}"

@router.post("", response_model=AssistanceResponse, status_code=status.HTTP_201_CREATED)
async def submit_assistance_request(
    request: Request,
    body: AssistanceSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Submits a new citizen assistance request.
    Evaluates risk and urgency immediately based strictly on threat signals.
    Subscription tier is NEVER considered in urgency evaluation.
    """
    # 1. Evaluate urgency
    eval_result = UrgencyEngine.evaluate(
        incident_type=body.incident_type,
        is_ongoing=body.is_ongoing_fraud,
        hours_since_incident=body.hours_since_incident,
        estimated_loss_inr=body.estimated_loss_inr or 0.0,
        has_compromised_credentials=body.has_compromised_credentials
    )
    urgency = eval_result["urgency_level"]

    # Map urgency to case priority
    priority_map = {
        "critical": CasePriority.critical,
        "high": CasePriority.high,
        "standard": CasePriority.medium
    }
    case_priority = priority_map.get(urgency, CasePriority.medium)

    # 2. Generate unique reference
    reference = generate_assistance_reference()
    case_id = uuid.uuid4()

    # 3. Create Case record
    new_case = Case(
        id=case_id,
        case_number=reference,
        assistance_reference=reference,
        submitted_by=user.id,
        scam_text=body.narrative,
        scam_type_code=body.incident_type.upper().replace(" ", "_"),
        city=body.city,
        state=body.state,
        victim_phone=body.victim_phone,
        estimated_amount=body.estimated_loss_inr,
        estimated_loss_inr=body.estimated_loss_inr,
        is_ongoing_fraud=body.is_ongoing_fraud,
        urgency_level=urgency,
        status=CaseStatus.submitted,
        priority=case_priority,
        triage_notes=f"Auto-evaluated urgency: {urgency.upper()}. Reasons: {'; '.join(eval_result['reasons'])}"
    )
    db.add(new_case)

    # 4. Create Initial Case Event
    init_event = CaseEvent(
        case_id=case_id,
        actor_id=user.id,
        actor_role=user.role,
        event_type="SUBMITTED",
        new_value=CaseStatus.submitted.value,
        description=f"Assistance request submitted with {urgency.upper()} urgency."
    )
    db.add(init_event)

    # 5. Create Audit Event
    audit_log = AuditEvent(
        actor_id=user.id,
        actor_role=user.role,
        action="ASSISTANCE_REQUEST_SUBMITTED",
        resource_type="case",
        resource_id=str(case_id),
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "reference": reference,
            "urgency_level": urgency,
            "is_ongoing": body.is_ongoing_fraud,
            "estimated_loss": body.estimated_loss_inr
        }
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(new_case)

    # 6. Publish to Event Bus if active
    try:
        from infrastructure.event_bus.redis_streams import RedisStreamEventBus
        from infrastructure.event_bus.catalog import EventCatalog
        event_bus = RedisStreamEventBus()
        await event_bus.publish(EventCatalog.CASE_CREATED, {
            "case_id": str(case_id),
            "reference": reference,
            "urgency_level": urgency,
            "user_id": str(user.id)
        })
    except Exception as exc:
        pass  # Non-blocking async event broadcast

    return AssistanceResponse(
        reference=reference,
        case_id=str(case_id),
        urgency_level=urgency,
        status=new_case.status.value,
        incident_type=body.incident_type,
        created_at=datetime.datetime.now(timezone.utc).isoformat(),
        emergency_guidance=eval_result["emergency_guidance"],
        reasons=eval_result["reasons"]
    )

@router.get("/mine")
async def get_my_assistance_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50
):
    """
    Returns assistance requests submitted by the logged-in citizen.
    """
    query = (
        select(Case)
        .where(Case.submitted_by == user.id)
        .order_by(desc(Case.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    cases = result.scalars().all()

    items = []
    for c in cases:
        items.append({
            "id": str(c.id),
            "reference": c.assistance_reference or c.case_number,
            "incident_type": c.scam_type_code,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "urgency_level": getattr(c, "urgency_level", "standard"),
            "is_ongoing_fraud": getattr(c, "is_ongoing_fraud", False),
            "estimated_loss_inr": getattr(c, "estimated_loss_inr", 0.0),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "city": c.city,
            "state": c.state
        })
    return {"requests": items, "count": len(items)}

@router.get("/{reference_or_id}")
async def get_assistance_request_detail(
    reference_or_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retrieves case details.
    Enforces authorization: Must be case owner, assigned officer, or admin.
    """
    # Try finding by ID or reference
    is_uuid = False
    try:
        val_uuid = uuid.UUID(reference_or_id)
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        query = select(Case).where(Case.id == val_uuid)
    else:
        query = select(Case).where(
            (Case.assistance_reference == reference_or_id) | (Case.case_number == reference_or_id)
        )

    res = await db.execute(query)
    c = res.scalars().first()

    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistance request not found")

    # Authorization Check
    is_owner = c.submitted_by == user.id
    is_assigned = getattr(c, "assigned_to", None) == user.id
    is_admin_or_police = user.role in ["admin", "police", "cyber_cell"]

    if not (is_owner or is_assigned or is_admin_or_police):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: You are not authorized to view this assistance request."
        )

    return {
        "id": str(c.id),
        "reference": c.assistance_reference or c.case_number,
        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
        "urgency_level": getattr(c, "urgency_level", "standard"),
        "incident_type": c.scam_type_code,
        "narrative": c.scam_text,
        "city": c.city,
        "state": c.state,
        "is_ongoing_fraud": getattr(c, "is_ongoing_fraud", False),
        "estimated_loss_inr": getattr(c, "estimated_loss_inr", 0.0),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "is_owner": is_owner
    }

@router.get("/{case_id}/events")
async def get_case_events(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns audit-safe timeline events for the assistance case.
    """
    try:
        c_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case UUID")

    # Verify authorization on the parent case
    c_res = await db.execute(select(Case).where(Case.id == c_uuid))
    case = c_res.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.submitted_by != user.id and user.role not in ["admin", "police", "cyber_cell"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    events_res = await db.execute(
        select(CaseEvent).where(CaseEvent.case_id == c_uuid).order_by(CaseEvent.created_at.asc())
    )
    events = events_res.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "actor_role": e.actor_role,
                "new_value": e.new_value,
                "description": e.description,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }


@router.get("/{reference_or_id}/dossier-pdf")
async def download_fir_dossier_pdf(
    reference_or_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user)
):
    """
    Generates a publication-quality Legal Cyber Incident Dossier (FIR Format) in A4 PDF.
    Exclusive Pro / Official Institutional capability.
    """
    is_uuid = False
    try:
        val_uuid = uuid.UUID(reference_or_id)
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        query = select(Case).where(Case.id == val_uuid)
    else:
        query = select(Case).where(
            (Case.assistance_reference == reference_or_id) | (Case.case_number == reference_or_id)
        )

    res = await db.execute(query)
    c = res.scalars().first()

    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistance request not found")

    # Authorization Check: Case owner, assigned officer, or admin
    is_owner = c.submitted_by == user.id
    is_assigned = getattr(c, "assigned_to", None) == user.id
    is_admin_or_police = user.role in ["admin", "police", "cyber_cell"]

    if not (is_owner or is_assigned or is_admin_or_police):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: You are not authorized to download this case dossier."
        )

    # Gather evidence items if available
    ev_items = []
    if hasattr(c, "evidence") and c.evidence:
        for ev in c.evidence:
            ev_items.append({
                "filename": ev.file_name if hasattr(ev, "file_name") else "Evidence File",
                "evidence_type": ev.evidence_type if hasattr(ev, "evidence_type") else "Document",
                "sha256": getattr(ev, "file_hash_sha256", "Pending")
            })

    ref_str = c.assistance_reference or c.case_number or str(c.id)[:8]
    date_str = c.created_at.strftime("%d %b %Y, %I:%M %p UTC") if c.created_at else datetime.datetime.now(timezone.utc).strftime("%d %b %Y")

    pdf_bytes = generate_fir_dossier_pdf(
        reference=ref_str,
        incident_type=c.scam_type_code or "Cyber Incident",
        urgency_level=getattr(c, "urgency_level", "standard"),
        incident_date=date_str,
        victim_name=user.full_name or "Complainant On File",
        victim_phone=c.assigned_phone or "",
        victim_city=c.city or "Not specified",
        victim_state=c.state or "Not specified",
        narrative=c.scam_text or "",
        estimated_loss_inr=getattr(c, "estimated_loss_inr", 0.0) or 0.0,
        evidence_items=ev_items,
    )

    # Log audit event
    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=user.id,
        actor_role=user.role,
        action="DOSSIER_PDF_DOWNLOADED",
        resource_type="case",
        resource_id=str(c.id),
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.datetime.now(timezone.utc),
        metadata_json={"reference": ref_str, "file_size_bytes": len(pdf_bytes)}
    )
    db.add(audit)
    await db.commit()

    filename = f"DigitalRakshak_FIR_Dossier_{ref_str}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
