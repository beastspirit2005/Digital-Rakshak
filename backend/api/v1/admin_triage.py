import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from infrastructure.db.session import get_db
from api.deps import get_current_admin
from domain.models.user import User
from domain.models.case import Case, CaseStatus, CasePriority
from domain.models.case_assignment import CaseAssignment
from domain.models.case_event import CaseEvent
from domain.models.audit_event import AuditEvent

router = APIRouter(prefix="/admin/cases", tags=["admin-triage"])

class AssignmentRequest(BaseModel):
    assignee_id: str = Field(..., description="UUID of the authorized officer")
    notes: Optional[str] = None

class TriageOverrideRequest(BaseModel):
    new_urgency: str = Field(..., description="critical, high, standard")
    override_reason: str = Field(..., min_length=5, description="Documented reason for overriding automated urgency")

class StatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description="under_review, in_progress, resolved, closed")
    resolution_notes: Optional[str] = None

@router.get("/queue")
async def get_triage_queue(
    request: Request,
    urgency: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_ongoing: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Administrative Case Triage Queue.
    Returns cases ordered by urgency priority (Critical -> High -> Standard) and age.
    """
    query = select(Case).order_by(
        desc(Case.priority),
        desc(Case.created_at)
    )

    if urgency:
        query = query.where(Case.urgency_level == urgency)
    if status_filter:
        query = query.where(Case.status == status_filter)
    if is_ongoing is not None:
        query = query.where(Case.is_ongoing_fraud == is_ongoing)

    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    cases = res.scalars().all()

    now = datetime.now(timezone.utc)
    queue = []
    for c in cases:
        age_hours = 0.0
        if c.created_at:
            # Normalize naive/aware datetime
            c_time = c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at
            age_hours = (now - c_time).total_seconds() / 3600.0

        # Calculate overdue SLA warning
        is_overdue = False
        urgency_val = getattr(c, "urgency_level", "standard")
        if urgency_val == "critical" and age_hours > 0.5 and c.status == CaseStatus.submitted:
            is_overdue = True
        elif urgency_val == "high" and age_hours > 4.0 and c.status == CaseStatus.submitted:
            is_overdue = True

        queue.append({
            "case_id": str(c.id),
            "reference": c.assistance_reference or c.case_number,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "urgency_level": urgency_val,
            "incident_type": c.scam_type_code,
            "narrative": c.scam_text,
            "city": c.city,
            "state": c.state,
            "is_ongoing_fraud": getattr(c, "is_ongoing_fraud", False),
            "estimated_loss_inr": getattr(c, "estimated_loss_inr", 0.0),
            "assigned_to": str(c.assigned_to) if getattr(c, "assigned_to", None) else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "age_hours": round(age_hours, 1),
            "is_overdue": is_overdue
        })

    return {"queue": queue, "total": len(queue)}

@router.post("/{case_id}/assign")
async def assign_case(
    case_id: str,
    body: AssignmentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Assigns an assistance request to an authorized official personnel account.
    """
    try:
        c_uuid = uuid.UUID(case_id)
        a_uuid = uuid.UUID(body.assignee_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID")

    # 1. Verify case
    c_res = await db.execute(select(Case).where(Case.id == c_uuid))
    case = c_res.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # 2. Verify assignee is an authorized officer
    u_res = await db.execute(select(User).where(User.id == a_uuid))
    assignee = u_res.scalars().first()
    if not assignee or assignee.role not in ["police", "cyber_cell", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be an active, verified police or cyber cell personnel."
        )

    # 3. Update case
    case.assigned_to = a_uuid
    case.status = CaseStatus.assigned
    case.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # 4. Create CaseAssignment
    assignment = CaseAssignment(
        case_id=c_uuid,
        assignee_id=a_uuid,
        assigned_by=admin.id,
        status="accepted",  # Direct administrative assignment
        responded_at=datetime.now(timezone.utc)
    )
    db.add(assignment)

    # 5. Case Event
    event = CaseEvent(
        case_id=c_uuid,
        actor_id=admin.id,
        actor_role=admin.role,
        event_type="ASSIGNED",
        old_value=None,
        new_value=str(a_uuid),
        description=f"Assigned to {assignee.full_name or assignee.email} ({assignee.role}). Notes: {body.notes or 'None'}"
    )
    db.add(event)

    # 6. Audit Event
    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="CASE_ASSIGNED",
        resource_type="case",
        resource_id=str(c_uuid),
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "assignee_id": str(a_uuid),
            "assignee_email": assignee.email,
            "assignee_role": assignee.role,
            "notes": body.notes
        }
    )
    db.add(audit)

    await db.commit()

    return {
        "status": "success",
        "message": f"Case successfully assigned to {assignee.full_name or assignee.email}",
        "case_id": str(c_uuid),
        "assignee_id": str(a_uuid)
    }

@router.post("/{case_id}/triage-override")
async def override_triage(
    case_id: str,
    body: TriageOverrideRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Overrides the automated urgency calculation with a mandatory recorded reason.
    """
    valid_urgencies = {"critical", "high", "standard"}
    if body.new_urgency not in valid_urgencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid urgency level. Must be one of: {', '.join(valid_urgencies)}"
        )

    try:
        c_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID")

    c_res = await db.execute(select(Case).where(Case.id == c_uuid))
    case = c_res.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    old_urgency = getattr(case, "urgency_level", "standard")
    case.urgency_level = body.new_urgency

    priority_map = {
        "critical": CasePriority.critical,
        "high": CasePriority.high,
        "standard": CasePriority.medium
    }
    case.priority = priority_map.get(body.new_urgency, CasePriority.medium)
    case.triage_notes = f"[Admin Override by {admin.email}]: {body.override_reason}"

    # Log Case Event
    event = CaseEvent(
        case_id=c_uuid,
        actor_id=admin.id,
        actor_role=admin.role,
        event_type="TRIAGE_OVERRIDE",
        old_value=old_urgency,
        new_value=body.new_urgency,
        description=f"Urgency manually overridden from {old_urgency.upper()} to {body.new_urgency.upper()}. Reason: {body.override_reason}"
    )
    db.add(event)

    # Log Audit Event
    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="TRIAGE_OVERRIDE",
        resource_type="case",
        resource_id=str(c_uuid),
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "old_urgency": old_urgency,
            "new_urgency": body.new_urgency,
            "reason": body.override_reason
        }
    )
    db.add(audit)

    await db.commit()

    return {
        "status": "success",
        "case_id": str(c_uuid),
        "old_urgency": old_urgency,
        "new_urgency": body.new_urgency,
        "reason": body.override_reason
    }
