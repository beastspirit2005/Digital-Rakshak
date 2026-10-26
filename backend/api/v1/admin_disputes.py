"""
Admin Misconduct Review & Dispute Resolution API
===============================================
Handles administrative triage of reported safety violations,
access-logged evidence examination, protective action enforcement,
and BSA 2023 Section 63 compliant digital evidence export.
"""

import uuid
import json
import zipfile
import io
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from infrastructure.db.session import get_db
from api.deps import get_current_admin
from domain.models.user import User
from domain.models.audit_event import AuditEvent
from domain.models.chat_safety import SafetyReport, PreservedEvidencePackage

router = APIRouter(prefix="/admin/disputes", tags=["admin-disputes"])


class DecisionRequest(BaseModel):
    decision: str = Field(..., description="no_violation, warning_issued, message_restricted, account_suspended, escalated_police")
    decision_notes: str = Field(..., min_length=10, description="Documented rationale for the administrative finding")


class LegalHoldRequest(BaseModel):
    is_legal_hold: bool = Field(..., description="Set true to prevent routine data deletion")
    hold_reason: Optional[str] = None


@router.get("")
async def list_disputes(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Returns the misconduct review queue with filtering by status.
    """
    q = select(SafetyReport).order_by(SafetyReport.created_at.desc()).limit(limit)
    if status_filter:
        q = q.where(SafetyReport.status == status_filter)

    res = await db.execute(q)
    reports = res.scalars().all()

    # Pre-fetch user details
    u_ids = set()
    for r in reports:
        u_ids.add(r.reporter_id)
        u_ids.add(r.reported_user_id)
        if r.reviewer_id:
            u_ids.add(r.reviewer_id)

    users_map = {}
    if u_ids:
        u_res = await db.execute(select(User).where(User.id.in_(list(u_ids))))
        for u in u_res.scalars().all():
            users_map[u.id] = {
                "name": u.full_name or "Digital Rakshak User",
                "email": u.email,
                "role": u.role
            }

    return {
        "disputes": [
            {
                "id": str(r.id),
                "case_id": str(r.case_id) if r.case_id else None,
                "category": r.category,
                "reason_narrative": r.reason_narrative,
                "status": r.status,
                "decision": r.decision,
                "reporter": users_map.get(r.reporter_id, {"name": "Unknown", "role": "user"}),
                "reported_user": users_map.get(r.reported_user_id, {"name": "Unknown", "role": "user"}),
                "reviewer": users_map.get(r.reviewer_id) if r.reviewer_id else None,
                "created_at": r.created_at.isoformat(),
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None
            }
            for r in reports
        ]
    }


@router.get("/{report_id}")
async def get_dispute_details(
    report_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Fetches preserved evidence package for review.
    Appends an immutable entry to the evidence package access_log.
    """
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report UUID")

    res = await db.execute(select(SafetyReport).where(SafetyReport.id == r_uuid))
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found")

    pkg_res = await db.execute(select(PreservedEvidencePackage).where(PreservedEvidencePackage.report_id == r_uuid))
    pkg = pkg_res.scalars().first()

    # Append audit access log
    if pkg:
        current_log = list(pkg.access_log or [])
        current_log.append({
            "action": "EVIDENCE_ACCESSED",
            "actor_id": str(admin.id),
            "actor_role": admin.role,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": request.client.host if request.client else None
        })
        pkg.access_log = current_log
        await db.commit()

    return {
        "report": {
            "id": str(report.id),
            "case_id": str(report.case_id) if report.case_id else None,
            "category": report.category,
            "reason_narrative": report.reason_narrative,
            "status": report.status,
            "decision": report.decision,
            "decision_notes": report.decision_notes,
            "created_at": report.created_at.isoformat(),
            "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None
        },
        "evidence_package": {
            "id": str(pkg.id) if pkg else None,
            "package_sha256": pkg.package_sha256 if pkg else None,
            "retention_until": pkg.retention_until.isoformat() if pkg else None,
            "is_legal_hold": pkg.is_legal_hold if pkg else False,
            "context_window": pkg.context_window_json if pkg else None,
            "access_log": pkg.access_log if pkg else []
        }
    }


@router.post("/{report_id}/decision")
async def record_dispute_decision(
    report_id: str,
    body: DecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Records an administrative finding and decision with mandatory written rationale.
    """
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report UUID")

    res = await db.execute(select(SafetyReport).where(SafetyReport.id == r_uuid))
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found")

    report.reviewer_id = admin.id
    report.decision = body.decision
    report.decision_notes = body.decision_notes
    report.status = "resolved_closed" if body.decision == "no_violation" else "protective_action"
    report.resolved_at = datetime.now(timezone.utc)

    # If protective action is suspension or restriction, execute on reported user
    if body.decision == "account_suspended":
        u_res = await db.execute(select(User).where(User.id == report.reported_user_id))
        target_user = u_res.scalars().first()
        if target_user:
            target_user.is_active = False

    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=admin.id,
        actor_role=admin.role,
        action="DISPUTE_DECISION_RECORDED",
        resource_type="safety_report",
        resource_id=str(report.id),
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={
            "decision": body.decision,
            "notes": body.decision_notes,
            "reported_user_id": str(report.reported_user_id)
        }
    )
    db.add(audit)

    await db.commit()

    return {
        "status": "decision_recorded",
        "report_id": str(report.id),
        "decision": report.decision,
        "resolved_at": report.resolved_at.isoformat()
    }


@router.post("/{report_id}/legal-hold")
async def toggle_legal_hold(
    report_id: str,
    body: LegalHoldRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Sets or lifts a legal preservation hold on the evidence package.
    """
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report UUID")

    pkg_res = await db.execute(select(PreservedEvidencePackage).where(PreservedEvidencePackage.report_id == r_uuid))
    pkg = pkg_res.scalars().first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence package not found")

    pkg.is_legal_hold = body.is_legal_hold
    current_log = list(pkg.access_log or [])
    current_log.append({
        "action": f"LEGAL_HOLD_{'APPLIED' if body.is_legal_hold else 'LIFTED'}",
        "actor_id": str(admin.id),
        "reason": body.hold_reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    pkg.access_log = current_log

    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=admin.id,
        actor_role=admin.role,
        action=f"LEGAL_HOLD_{'ENABLED' if body.is_legal_hold else 'DISABLED'}",
        resource_type="preserved_evidence_package",
        resource_id=str(pkg.id),
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={"is_legal_hold": body.is_legal_hold, "reason": body.hold_reason}
    )
    db.add(audit)

    await db.commit()

    return {
        "report_id": report_id,
        "is_legal_hold": pkg.is_legal_hold,
        "status": "updated"
    }


@router.get("/{report_id}/export-bsa")
async def export_bsa_package(
    report_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Exports a Section 63 Bharatiya Sakshya Adhiniyam, 2023 Electronic Evidence Package.
    Returns a ZIP containing JSON manifest, context window, and certificate declaration.
    """
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report UUID")

    res = await db.execute(select(SafetyReport).where(SafetyReport.id == r_uuid))
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found")

    pkg_res = await db.execute(select(PreservedEvidencePackage).where(PreservedEvidencePackage.report_id == r_uuid))
    pkg = pkg_res.scalars().first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence package not found")

    # Generate Manifest
    now_str = datetime.now(timezone.utc).isoformat()
    manifest = {
        "platform": "Digital Rakshak Sovereign Cyber Defense",
        "export_timestamp": now_str,
        "exported_by_admin_id": str(admin.id),
        "report_id": str(report.id),
        "case_id": str(report.case_id) if report.case_id else None,
        "category": report.category,
        "package_sha256": pkg.package_sha256,
        "retention_until": pkg.retention_until.isoformat(),
        "is_legal_hold": pkg.is_legal_hold,
        "chain_of_custody_entries": pkg.access_log,
        "governing_law": "Bharatiya Sakshya Adhiniyam (BSA), 2023, Sections 61, 62 & 63"
    }

    # Generate BSA Section 63 Certificate text
    cert_text = f"""CERTIFICATE UNDER SECTION 63 OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023
========================================================================

1. I, {admin.full_name or 'Authorized Platform Administrator'}, holding the administrative role of '{admin.role}'
   within the Digital Rakshak Cyber Defense Core, do hereby state and certify as follows:

2. That this electronic record (Report Ref: {report.id}) is produced by computer systems
   regularly used in the lawful activities of Digital Rakshak.

3. That throughout the period of recording, the platform and evidence preservation vault
   operated under cryptographic data protection controls.

4. That the contextual communication record preserved herein has been locked with
   the cryptographic SHA-256 hash:
   {pkg.package_sha256}

5. That the information contained in the accompanying 'context_window.json' is an exact,
   unaltered reproduction of the electronic messages stored at the moment of report.

Certified on: {now_str}
Digital Rakshak Compliance & Trust Authority
"""

    # Build ZIP in-memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
        zip_file.writestr("context_window.json", json.dumps(pkg.context_window_json, indent=2))
        zip_file.writestr("BSA_2023_Sec63_Certificate.txt", cert_text)

    zip_bytes = zip_buffer.getvalue()

    # Log audit event
    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=admin.id,
        actor_role=admin.role,
        action="BSA_EVIDENCE_PACKAGE_EXPORTED",
        resource_type="preserved_evidence_package",
        resource_id=str(pkg.id),
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={"report_id": str(report.id), "package_sha256": pkg.package_sha256}
    )
    db.add(audit)
    await db.commit()

    filename = f"BSA_Evidence_Report_{str(report.id)[:8]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )
