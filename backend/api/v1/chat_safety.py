"""
Chat Safety & Misconduct Reporting API
=====================================
Handles chat transparency policy consent, real-time message moderation,
and cryptographic context-window preservation for misconduct reporting.
"""

import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from infrastructure.db.session import get_db
from api.deps import get_current_user
from domain.models.user import User
from domain.models.case import Case
from domain.models.case_event import CaseEvent
from domain.models.audit_event import AuditEvent
from domain.models.chat_safety import CaseMessage, SafetyReport, PreservedEvidencePackage
from domain.services.chat_safety_scanner import ChatSafetyScanner, ScanResult

router = APIRouter(prefix="/chat", tags=["chat-safety"])

POLICY_VERSION = "v1.0"


class AcknowledgePolicyRequest(BaseModel):
    policy_version: str = Field(POLICY_VERSION, description="Version of the chat safety notice accepted")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    attachments: Optional[List[Dict[str, Any]]] = None


class ReportMisconductRequest(BaseModel):
    case_id: Optional[str] = None
    reported_message_id: Optional[str] = None
    reported_user_id: str
    category: str = Field(..., description="payment_demand, credential_harvesting, harassment, impersonation, recovery_scam")
    reason_narrative: str = Field(..., min_length=10)


@router.get("/policy-status")
async def get_policy_status(user: User = Depends(get_current_user)):
    """
    Returns whether the authenticated user has accepted the latest Chat Transparency Notice.
    """
    accepted = (user.chat_safety_policy_version == POLICY_VERSION)
    return {
        "policy_version": POLICY_VERSION,
        "is_accepted": accepted,
        "accepted_at": user.chat_safety_accepted_at.isoformat() if user.chat_safety_accepted_at else None,
        "transparency_terms": [
            "All messages are inspected in real time by automated security safeguards.",
            "Sharing passwords, OTPs, UPI PINs, or CVVs is strictly forbidden and blocked.",
            "Official police and investigators will NEVER demand fees, bribes, or advance payments.",
            "When misconduct is reported, an immutable snapshot of surrounding messages is cryptographically preserved.",
            "Tamper-evident evidence packages comply with Bharatiya Sakshya Adhiniyam (BSA), 2023.",
        ]
    }


@router.post("/acknowledge-policy")
async def acknowledge_policy(
    body: AcknowledgePolicyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Records timestamped consent to the Chat Safety and Monitoring Notice.
    """
    user.chat_safety_policy_version = POLICY_VERSION
    user.chat_safety_accepted_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "status": "acknowledged",
        "policy_version": POLICY_VERSION,
        "accepted_at": user.chat_safety_accepted_at.isoformat()
    }


@router.post("/cases/{case_id}/messages")
async def send_case_message(
    case_id: str,
    body: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Sends a message within a case thread. Runs real-time safety inspection.
    Blocks delivery if authentication secrets or SSRF hazards are detected.
    """
    try:
        c_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    # Authorize case participant
    c_res = await db.execute(select(Case).where(Case.id == c_uuid))
    case = c_res.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    is_owner = case.submitted_by == user.id
    is_assigned = getattr(case, "assigned_to", None) == user.id
    is_admin_or_police = user.role in ["admin", "police", "cyber_cell"]

    if not (is_owner or is_assigned or is_admin_or_police):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to post to this case")

    # Run inspection engine
    scan = ChatSafetyScanner.scan_message(body.content)

    if scan.is_blocked:
        # Hard block delivery
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "DELIVERY_BLOCKED",
                "reason": scan.alert_message,
                "rule": scan.rule,
                "indicators": scan.detected_indicators
            }
        )

    msg = CaseMessage(
        id=uuid.uuid4(),
        case_id=c_uuid,
        sender_id=user.id,
        content=scan.sanitized_content,
        attachments=body.attachments or [],
        moderation_flag=scan.flag,
        scanner_rule=scan.rule,
        is_redacted=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(msg)

    # Event log for case
    event = CaseEvent(
        id=uuid.uuid4(),
        case_id=c_uuid,
        actor_id=user.id,
        actor_role=user.role,
        event_type="MESSAGE_SENT",
        new_value=scan.flag,
        description=f"Message posted with moderation flag: {scan.flag}",
        metadata_json={"scanner_rule": scan.rule, "warning": scan.alert_message} if scan.rule else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)

    await db.commit()
    await db.refresh(msg)

    return {
        "id": str(msg.id),
        "case_id": str(msg.case_id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "moderation_flag": msg.moderation_flag,
        "warning_alert": scan.alert_message,
        "created_at": msg.created_at.isoformat(),
        "attachments": msg.attachments
    }


@router.get("/cases/{case_id}/messages")
async def get_case_messages(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retrieves message history for a case. Requires participant or authorized role.
    """
    try:
        c_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

    c_res = await db.execute(select(Case).where(Case.id == c_uuid))
    case = c_res.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    is_owner = case.submitted_by == user.id
    is_assigned = getattr(case, "assigned_to", None) == user.id
    is_admin_or_police = user.role in ["admin", "police", "cyber_cell"]

    if not (is_owner or is_assigned or is_admin_or_police):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    q = select(CaseMessage).where(CaseMessage.case_id == c_uuid).order_by(CaseMessage.created_at.asc())
    msgs = (await db.execute(q)).scalars().all()

    # Pre-fetch senders to display name/role
    sender_ids = list({m.sender_id for m in msgs})
    senders_map = {}
    if sender_ids:
        u_res = await db.execute(select(User).where(User.id.in_(sender_ids)))
        for u in u_res.scalars().all():
            senders_map[u.id] = {
                "name": u.full_name or "Official User",
                "role": u.role
            }

    return {
        "messages": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "sender_name": senders_map.get(m.sender_id, {}).get("name", "User"),
                "sender_role": senders_map.get(m.sender_id, {}).get("role", "citizen"),
                "is_self": m.sender_id == user.id,
                "content": m.content,
                "moderation_flag": m.moderation_flag,
                "attachments": m.attachments or [],
                "created_at": m.created_at.isoformat()
            }
            for m in msgs
        ]
    }


@router.post("/safety-reports")
async def report_misconduct(
    body: ReportMisconductRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Submits a misconduct allegation.
    Snapshots the Context Window (reported message + 5 preceding + 2 succeeding),
    calculates cryptographic SHA-256 digest, and creates a protected evidence record.
    """
    try:
        reported_user_uuid = uuid.UUID(body.reported_user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reported user ID")

    case_uuid = None
    if body.case_id:
        try:
            case_uuid = uuid.UUID(body.case_id)
        except ValueError:
            pass

    msg_uuid = None
    reported_msg = None
    if body.reported_message_id:
        try:
            msg_uuid = uuid.UUID(body.reported_message_id)
            m_res = await db.execute(select(CaseMessage).where(CaseMessage.id == msg_uuid))
            reported_msg = m_res.scalars().first()
            if reported_msg and not case_uuid:
                case_uuid = reported_msg.case_id
        except ValueError:
            pass

    # Context Window Preservation: 5 before, target message, 2 after
    context_msgs = []
    if case_uuid:
        if reported_msg:
            # 5 preceding
            before_q = select(CaseMessage).where(
                CaseMessage.case_id == case_uuid,
                CaseMessage.created_at < reported_msg.created_at
            ).order_by(CaseMessage.created_at.desc()).limit(5)
            before_msgs = list(reversed((await db.execute(before_q)).scalars().all()))

            # 2 succeeding
            after_q = select(CaseMessage).where(
                CaseMessage.case_id == case_uuid,
                CaseMessage.created_at > reported_msg.created_at
            ).order_by(CaseMessage.created_at.asc()).limit(2)
            after_msgs = (await db.execute(after_q)).scalars().all()

            context_msgs = before_msgs + [reported_msg] + after_msgs
        else:
            # Most recent 10 messages from the case
            recent_q = select(CaseMessage).where(CaseMessage.case_id == case_uuid).order_by(CaseMessage.created_at.desc()).limit(10)
            context_msgs = list(reversed((await db.execute(recent_q)).scalars().all()))

    # Build canonical context dictionary
    context_window = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": str(user.id),
        "reported_user_id": str(reported_user_uuid),
        "category": body.category,
        "reason_narrative": body.reason_narrative,
        "messages": [
            {
                "message_id": str(m.id),
                "sender_id": str(m.sender_id),
                "content": m.content,
                "moderation_flag": m.moderation_flag,
                "scanner_rule": m.scanner_rule,
                "attachments": m.attachments or [],
                "created_at": m.created_at.isoformat(),
                "is_target": (str(m.id) == str(msg_uuid)) if msg_uuid else False
            }
            for m in context_msgs
        ]
    }

    # Cryptographic Digest Computation
    canonical_bytes = json.dumps(context_window, sort_keys=True).encode("utf-8")
    package_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

    # Create Safety Report
    report_id = uuid.uuid4()
    report = SafetyReport(
        id=report_id,
        case_id=case_uuid,
        reported_message_id=msg_uuid,
        reporter_id=user.id,
        reported_user_id=reported_user_uuid,
        category=body.category,
        reason_narrative=body.reason_narrative,
        status="pending_review",
        created_at=datetime.now(timezone.utc),
    )
    db.add(report)

    # Create Preserved Evidence Package (180 days default retention)
    retention_date = datetime.now(timezone.utc) + timedelta(days=180)
    package = PreservedEvidencePackage(
        id=uuid.uuid4(),
        report_id=report_id,
        case_id=case_uuid,
        context_window_json=context_window,
        package_sha256=package_sha256,
        retention_until=retention_date,
        is_legal_hold=False,
        access_log=[
            {
                "action": "EVIDENCE_PRESERVED",
                "actor_id": str(user.id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip": request.client.host if request.client else None
            }
        ],
        created_at=datetime.now(timezone.utc),
    )
    db.add(package)

    # Audit log
    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=user.id,
        actor_role=user.role,
        action="SAFETY_MISCONDUCT_REPORTED",
        resource_type="safety_report",
        resource_id=str(report_id),
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={"category": body.category, "package_sha256": package_sha256}
    )
    db.add(audit)

    await db.commit()

    return {
        "report_id": str(report.id),
        "status": report.status,
        "category": report.category,
        "evidence_package_sha256": package_sha256,
        "retention_until": retention_date.isoformat(),
        "message": "Misconduct report registered. Evidence context window preserved with SHA-256 seal for admin review."
    }
