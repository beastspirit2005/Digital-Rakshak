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


MAX_EVIDENCE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".dll", 
    ".scr", ".pif", ".com", ".msi", ".php", ".jsp", ".asp", ".cgi"
}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    case_id: Optional[uuid.UUID] = Form(None),
    evidence_type: str = Form("screenshot"),
    content_text: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Ingests raw digital evidence into the Evidence Vault Repository (EVR).
    Calculates cryptographic SHA-256 digest, records upload attributes, and appends an initial Chain of Custody log.
    Validates file extension, maximum file size (25MB), and enforces access control.
    """
    # 1. Filename & Extension validation
    fname = file.filename or "uploaded_artifact"
    _, ext = os.path.splitext(fname.lower())
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disallowed executable or script file extension '{ext}'. Uploading executable payloads is prohibited."
        )

    try:
        repo = EvidenceRepository(db)
        actor_name = f"{user.full_name or user.email} ({user.role})"
        owner_id = user.id

        # 2. Check byte length via hash method
        sha256_hex, file_size = await repo.hash(file)
        if file_size > MAX_EVIDENCE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum permitted limit of 25MB."
            )

        evidence = await repo.store(
            file_obj=file,
            filename=fname,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EVR Upload Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evidence Vault upload error: {str(e)}")


async def _check_evidence_access(evidence: Evidence, user: Optional[User], db: AsyncSession) -> None:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access Evidence Vault artifacts.",
        )
    # Institutional roles: Admin and Police/Cyber Cell have authorized forensic access
    if user.role in ["admin", "police", "cyber_cell"]:
        return

    # Bank officers are strictly restricted to financial scam cases (CS-03 BOLA Hardening)
    if user.role in ["banker", "bank_employee"]:
        if not evidence.case_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bank officers are only authorized to access evidence attached to financial fraud cases.",
            )
        from domain.models.case import Case
        case_res = await db.execute(select(Case).where(Case.id == evidence.case_id))
        case = case_res.scalars().first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated case not found for this evidence artifact.",
            )
        scam_code = (case.scam_type_code or "").upper()
        financial_keywords = ("FIN", "BANK", "UPI", "PAY", "CARD", "LOAN", "INVEST", "CRYPTO", "MULE", "FRAUD", "TXN")
        is_financial = any(kw in scam_code for kw in financial_keywords)
        if not is_financial:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Bank officers are only authorized to view evidence associated with financial fraud investigations.",
            )
        return

    # Citizens can only access their own submitted evidence
    if evidence.evidence_owner and evidence.evidence_owner == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this evidence artifact.",
    )


@router.get("/{evidence_id}")
async def get_evidence_details(
    evidence_id: uuid.UUID,
    verify_now: bool = Query(False, description="Run real-time disk SHA-256 comparison before returning"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retrieves evidence metadata and integrity status.
    If verify_now=True, re-reads file from storage location and checks SHA-256 digest match.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")

    await _check_evidence_access(evidence, user, db)

    repo = EvidenceRepository(db)

    if verify_now:
        actor_name = f"{user.full_name} ({user.role})" if user else "API Validator"
        verification_result = await repo.verify(evidence_id, actor=actor_name)
        if verification_result.get("status") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Evidence artifact not found in database")

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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns the legally traceable chronological Chain of Custody audit log for an evidence artifact.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")

    await _check_evidence_access(evidence, user, db)

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
    user: User = Depends(get_current_user)
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
    user: User = Depends(get_current_user)
):
    """
    Streams the original raw evidence file with exact MIME type and Chain of Custody access logging.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()

    path_to_check = evidence.storage_location or evidence.file_path
    if not evidence or not path_to_check:
        raise HTTPException(status_code=404, detail="Evidence file missing or not found on server")

    await _check_evidence_access(evidence, user, db)

    # Record access log
    repo = EvidenceRepository(db)
    actor_name = f"{user.full_name} ({user.role})" if user else "Investigator / Viewer"
    await repo.log_access(evidence_id, actor=actor_name, action="HUMAN_REVIEW", remarks=f"{actor_name} downloaded/previewed evidence file.")

    if path_to_check.startswith("supabase://"):
        from core.config import settings
        from fastapi.responses import RedirectResponse, StreamingResponse
        import io
        bucket, filename = path_to_check.replace("supabase://", "").split("/", 1)
        try:
            from infrastructure.storage.supabase_storage import supabase_storage
            if supabase_storage.is_configured:
                file_bytes = await supabase_storage.download_file(bucket, filename)
                if file_bytes:
                    return StreamingResponse(
                        io.BytesIO(file_bytes),
                        media_type=evidence.mime_type or "application/octet-stream",
                        headers={"Content-Disposition": f'inline; filename="{filename}"'}
                    )
        except Exception as e:
            logger.warning(f"Supabase download failed in evidence router: {e}")
            
        # If Supabase failed, check if we have a local fallback in uploads/evidence_vault
        local_path = os.path.join(repo.upload_dir, filename)
    elif path_to_check.startswith("local://"):
        local_path = os.path.join(repo.upload_dir, path_to_check.replace("local://", ""))
    else:
        local_path = path_to_check

    if not os.path.exists(local_path):
        # Try one last fallback using just the filename
        fallback_path = os.path.join(repo.upload_dir, os.path.basename(path_to_check))
        if os.path.exists(fallback_path):
            local_path = fallback_path
        else:
            raise HTTPException(status_code=404, detail="Evidence file missing or not found on storage backend")

    safe_filename = os.path.basename(local_path)
    return FileResponse(
        path=local_path,
        media_type=evidence.mime_type or "application/octet-stream",
        filename=safe_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "Content-Security-Policy": "default-src 'none'",
            "X-Frame-Options": "DENY",
        }
    )
