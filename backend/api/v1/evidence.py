import os
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.db.session import get_db
from infrastructure.repositories.evidence_repository import EvidenceRepository
from domain.models.evidence import Evidence, ChainOfCustodyLog
from domain.models.user import User
from api.deps import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["Evidence Vault Repository (EVR)"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    case_id: Optional[uuid.UUID] = Form(None),
    evidence_type: str = Form("screenshot"),
    content_text: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Ingests raw digital evidence into the Evidence Vault Repository (EVR).
    Calculates cryptographic SHA-256 digest, records upload attributes, and appends an initial Chain of Custody log.
    """
    try:
        repo = EvidenceRepository(db)
        actor_name = f"{user.full_name} ({user.role})" if user else "Citizen (Submitter)"
        owner_id = user.id if user else None

        evidence = await repo.store(
            file_obj=file,
            filename=file.filename or "uploaded_artifact",
            mime_type=file.content_type or "application/octet-stream",
            evidence_type=evidence_type,
            actor=actor_name,
            owner_id=owner_id,
            case_id=case_id,
            content_text=content_text,
            source="evr_upload_api"
        )

        return {
            "status": "success",
            "evidence": {
                "id": str(evidence.id),
                "case_id": str(evidence.case_id) if evidence.case_id else None,
                "evidence_type": evidence.evidence_type,
                "mime_type": evidence.mime_type,
                "sha256": evidence.sha256,
                "file_size_bytes": evidence.file_size_bytes,
                "integrity_status": evidence.integrity_status,
                "created_at": evidence.created_at.isoformat() if evidence.created_at else None
            }
        }
    except Exception as e:
        logger.error(f"EVR Upload Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evidence Vault upload error: {str(e)}")


@router.get("/{evidence_id}")
async def get_evidence_details(
    evidence_id: uuid.UUID,
    verify_now: bool = Query(False, description="Run real-time disk SHA-256 comparison before returning"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieves evidence metadata and integrity status.
    If verify_now=True, re-reads file from storage location and checks SHA-256 digest match.
    """
    repo = EvidenceRepository(db)

    if verify_now:
        actor_name = f"{user.full_name} ({user.role})" if user else "API Validator"
        verification_result = await repo.verify(evidence_id, actor=actor_name)
        if verification_result.get("status") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Evidence artifact not found in database")

    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")

    return {
        "id": str(evidence.id),
        "case_id": str(evidence.case_id) if evidence.case_id else None,
        "evidence_type": evidence.evidence_type,
        "mime_type": evidence.mime_type,
        "sha256": evidence.sha256 or evidence.file_hash_sha256,
        "file_size_bytes": evidence.file_size_bytes,
        "storage_location": evidence.storage_location,
        "integrity_status": evidence.integrity_status,
        "content_text": evidence.content_text,
        "evidence_owner": str(evidence.evidence_owner) if evidence.evidence_owner else None,
        "created_at": evidence.created_at.isoformat() if evidence.created_at else None
    }


@router.get("/{evidence_id}/history")
async def get_chain_of_custody_history(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the legally traceable chronological Chain of Custody audit log for an evidence artifact.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Evidence artifact not found")

    repo = EvidenceRepository(db)
    history = await repo.get_history(evidence_id)

    return {
        "evidence_id": str(evidence_id),
        "total_records": len(history),
        "chain_of_custody": [
            {
                "id": str(log.id),
                "actor": log.actor,
                "action": log.action,
                "remarks": log.remarks,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            } for log in history
        ]
    }


@router.post("/{evidence_id}/verify")
async def verify_evidence_integrity(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Manually triggers an explicit cryptographic SHA-256 check against the disk artifact.
    Appends a VERIFIED entry into the Chain of Custody audit ledger.
    """
    repo = EvidenceRepository(db)
    actor_name = f"{user.full_name} ({user.role})" if user else "Investigator / System"
    verification = await repo.verify(evidence_id, actor=actor_name)

    if verification.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Evidence artifact not found")

    return verification


@router.get("/{evidence_id}/download")
async def download_evidence_file(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Streams the original raw evidence file with exact MIME type and Chain of Custody access logging.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()

    if not evidence or not evidence.storage_location or not os.path.exists(evidence.storage_location):
        raise HTTPException(status_code=404, detail="Evidence file missing or not found on server")

    # Record access log
    repo = EvidenceRepository(db)
    actor_name = f"{user.full_name} ({user.role})" if user else "Investigator / Viewer"
    await repo.log_access(evidence_id, actor=actor_name, action="HUMAN_REVIEW", remarks=f"{actor_name} downloaded/previewed evidence file.")

    return FileResponse(
        path=evidence.storage_location,
        media_type=evidence.mime_type or "application/octet-stream",
        filename=os.path.basename(evidence.storage_location)
    )
