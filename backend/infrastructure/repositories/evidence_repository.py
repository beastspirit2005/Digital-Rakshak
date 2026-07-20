import os
import uuid
import hashlib
import logging
from typing import Optional, List, Tuple, BinaryIO, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile

from domain.models.evidence import Evidence, EvidenceType, ChainOfCustodyLog
from core.config import settings

logger = logging.getLogger(__name__)


class EvidenceRepository:
    """
    Module 1 — Evidence Vault Repository (EVR)
    Responsible for transforming uploaded files into legally traceable digital evidence.
    Enforces SHA-256 cryptographic digests, immutable snapshots, and Chain of Custody audit logs.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Ensure evidence upload directory exists
        self.upload_dir = os.path.join(settings.UPLOAD_DIR, "evidence_vault")
        os.makedirs(self.upload_dir, exist_ok=True)

    async def hash(self, file_obj: Union[UploadFile, BinaryIO, bytes]) -> Tuple[str, int]:
        """
        Computes SHA-256 digest and total byte count for a file object or byte stream.
        Reads in chunks to prevent high memory consumption on large APK/Video evidence.
        """
        sha256_hasher = hashlib.sha256()
        total_bytes = 0

        if isinstance(file_obj, bytes):
            sha256_hasher.update(file_obj)
            return sha256_hasher.hexdigest(), len(file_obj)

        # Handle FastAPI UploadFile
        if hasattr(file_obj, "seek") and hasattr(file_obj, "read"):
            if hasattr(file_obj, "seekable") and callable(file_obj.seekable) and file_obj.seekable():
                file_obj.seek(0)
            elif hasattr(file_obj, "seek") and callable(file_obj.seek):
                try:
                    await file_obj.seek(0) if hasattr(file_obj.seek, "__await__") else file_obj.seek(0)
                except Exception:
                    pass

            while True:
                read_func = file_obj.read
                chunk = await read_func(65536) if hasattr(read_func, "__await__") else read_func(65536)
                if not chunk:
                    break
                sha256_hasher.update(chunk)
                total_bytes += len(chunk)

            # Reset cursor after reading
            if hasattr(file_obj, "seek") and callable(file_obj.seek):
                try:
                    await file_obj.seek(0) if hasattr(file_obj.seek, "__await__") else file_obj.seek(0)
                except Exception:
                    pass

        return sha256_hasher.hexdigest(), total_bytes

    async def store(
        self,
        file_obj: Union[UploadFile, bytes],
        filename: str,
        mime_type: str,
        evidence_type: str,
        actor: str = "Citizen (Submitter)",
        owner_id: Optional[uuid.UUID] = None,
        case_id: Optional[uuid.UUID] = None,
        content_text: Optional[str] = None,
        source: str = "evr_upload"
    ) -> Evidence:
        """
        Stores uploaded evidence with cryptographic SHA-256 calculation and Chain of Custody logging.
        """
        # 1. Compute Hash and Size
        sha256_hex, file_size = await self.hash(file_obj)

        # 2. Save binary to secure disk path inside evidence_vault
        unique_filename = f"{uuid.uuid4()}_{os.path.basename(filename or 'artifact.bin')}"
        storage_path = os.path.join(self.upload_dir, unique_filename)

        if isinstance(file_obj, bytes):
            with open(storage_path, "wb") as f:
                f.write(file_obj)
        else:
            with open(storage_path, "wb") as f:
                while True:
                    read_func = file_obj.read
                    chunk = await read_func(65536) if hasattr(read_func, "__await__") else read_func(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if hasattr(file_obj, "seek") and callable(file_obj.seek):
                try:
                    await file_obj.seek(0) if hasattr(file_obj.seek, "__await__") else file_obj.seek(0)
                except Exception:
                    pass

        # 3. Create Evidence DB Record
        evidence = Evidence(
            case_id=case_id,
            evidence_owner=owner_id,
            evidence_type=evidence_type,
            mime_type=mime_type,
            file_path=storage_path,
            storage_location=storage_path,
            sha256=sha256_hex,
            file_hash_sha256=sha256_hex,
            file_size_bytes=file_size,
            content_text=content_text,
            integrity_status="VERIFIED",
            source=source
        )
        self.db.add(evidence)
        await self.db.flush()

        # 4. Record Initial Chain of Custody Log
        coc_log = ChainOfCustodyLog(
            evidence_id=evidence.id,
            actor=actor,
            action="UPLOADED",
            remarks=f"Ingested via EVR. SHA-256 verified: {sha256_hex} ({file_size} bytes)."
        )
        self.db.add(coc_log)
        await self.db.commit()
        await self.db.refresh(evidence)

        logger.info(f"Stored Evidence {evidence.id} with SHA-256 {sha256_hex}")
        return evidence

    async def verify(self, evidence_id: uuid.UUID, actor: str = "System Validator") -> dict:
        """
        Re-calculates disk file SHA-256 digest and compares against database record (`sha256`).
        Records verification action in Chain of Custody.
        """
        result = await self.db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = result.scalars().first()

        if not evidence:
            return {"is_valid": False, "status": "NOT_FOUND", "error": "Evidence record does not exist."}

        path_to_check = evidence.storage_location or evidence.file_path

        disk_bytes = None
        if path_to_check and path_to_check.startswith("supabase://"):
            from core.config import settings
            from supabase import create_client
            bucket, filename = path_to_check.replace("supabase://", "").split("/", 1)
            try:
                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                disk_bytes = supabase.storage.from_(bucket).download(filename)
            except Exception as e:
                logger.error(f"Failed to fetch evidence from Supabase for verification: {e}")
                # Fallback to local disk using the filename
                local_fallback = os.path.join(self.upload_dir, filename)
                if os.path.exists(local_fallback):
                    with open(local_fallback, "rb") as f:
                        disk_bytes = f.read()
        
        if disk_bytes is None and path_to_check:
            local_path = path_to_check
            if path_to_check.startswith("local://"):
                local_path = os.path.join(self.upload_dir, path_to_check.replace("local://", ""))
            
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    disk_bytes = f.read()
            elif not path_to_check.startswith("supabase://"):
                # One last attempt: check if it's just a filename in upload_dir
                fallback = os.path.join(self.upload_dir, os.path.basename(path_to_check))
                if os.path.exists(fallback):
                    with open(fallback, "rb") as f:
                        disk_bytes = f.read()

        if disk_bytes is None:
            evidence.integrity_status = "TAMPERED"
            coc_log = ChainOfCustodyLog(
                evidence_id=evidence.id,
                actor=actor,
                action="VERIFIED",
                remarks="Verification FAILED: File missing from storage location on disk or cloud."
            )
            self.db.add(coc_log)
            await self.db.commit()
            return {"is_valid": False, "status": "TAMPERED", "error": "File missing on storage backend."}

        sha256_hasher = hashlib.sha256(disk_bytes)
        disk_sha256 = sha256_hasher.hexdigest()

        is_match = (disk_sha256 == evidence.sha256) or (disk_sha256 == evidence.file_hash_sha256)
        new_status = "VERIFIED" if is_match else "TAMPERED"
        evidence.integrity_status = new_status

        coc_log = ChainOfCustodyLog(
            evidence_id=evidence.id,
            actor=actor,
            action="VERIFIED",
            remarks=f"Integrity check {'PASSED' if is_match else 'FAILED'}. Storage SHA-256: {disk_sha256}."
        )
        self.db.add(coc_log)
        await self.db.commit()

        return {
            "is_valid": is_match,
            "status": new_status,
            "sha256": disk_sha256,
            "expected_sha256": evidence.sha256 or evidence.file_hash_sha256,
            "file_size": len(disk_bytes)
        }

    async def archive(self, evidence_id: uuid.UUID, actor: str = "System Admin", remarks: str = "Archived post-case closure") -> Optional[Evidence]:
        """
        Transitions evidence to ARCHIVED status and logs to Chain of Custody.
        """
        result = await self.db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = result.scalars().first()

        if not evidence:
            return None

        evidence.integrity_status = "ARCHIVED"
        coc_log = ChainOfCustodyLog(
            evidence_id=evidence.id,
            actor=actor,
            action="ARCHIVED",
            remarks=remarks
        )
        self.db.add(coc_log)
        await self.db.commit()
        await self.db.refresh(evidence)
        return evidence

    async def get_history(self, evidence_id: uuid.UUID) -> List[ChainOfCustodyLog]:
        """
        Retrieves the complete chronological Chain of Custody audit log for an evidence artifact.
        """
        result = await self.db.execute(
            select(ChainOfCustodyLog)
            .where(ChainOfCustodyLog.evidence_id == evidence_id)
            .order_by(ChainOfCustodyLog.timestamp.asc())
        )
        return list(result.scalars().all())

    async def log_access(self, evidence_id: uuid.UUID, actor: str, action: str, remarks: Optional[str] = None) -> ChainOfCustodyLog:
        """
        Utility to record AI or Human access events (e.g. 'AI: OCRAnalysisAgent read evidence').
        """
        coc_log = ChainOfCustodyLog(
            evidence_id=evidence_id,
            actor=actor,
            action=action,
            remarks=remarks or f"{actor} performed {action}"
        )
        self.db.add(coc_log)
        await self.db.commit()
        await self.db.refresh(coc_log)
        return coc_log
