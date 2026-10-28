import os
import uuid
import hashlib
from typing import Tuple
from fastapi import UploadFile, HTTPException, status

MAX_KYC_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

MAGIC_NUMBERS = {
    "pdf": b"%PDF-",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
    "webp": b"RIFF"  # and bytes 8-12 == b"WEBP"
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


async def validate_and_save_kyc_file(
    file: UploadFile,
    user_id: uuid.UUID,
    doc_type: str
) -> Tuple[str, str, str]:
    """
    Enterprise Zero-Trust KYC File Validator:
    1. Validates file extension against strict whitelist.
    2. Inspects magic bytes (file signature) to detect polyglot / spoofed files.
    3. Enforces strict 5MB maximum file size limit.
    4. Computes SHA-256 cryptographic digest.
    5. Saves file securely in isolated storage directory (uploads/kyc/{user_id}/{uuid}.{ext})
       outside the public web root with randomized safe filename.

    Returns:
        (stored_relative_path, original_sanitized_filename, sha256_hex)
    """
    raw_name = file.filename or f"{doc_type}.dat"
    # Sanitize original filename (strip directories, traversal tokens)
    clean_base = os.path.basename(raw_name).replace("\\", "/").split("/")[-1]
    # Remove null bytes or non-printable chars
    clean_base = "".join(c for c in clean_base if c.isalnum() or c in ".-_ ")
    if not clean_base:
        clean_base = f"{doc_type}.dat"

    _, ext = os.path.splitext(clean_base.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disallowed file extension '{ext}'. Only PDF, JPEG, PNG, and WebP documents are permitted."
        )

    # 1. Read first 512 bytes for Magic Number inspection
    header = await file.read(512)
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{clean_base}' is empty (0 bytes)."
        )

    # 2. Verify file binary signature
    is_valid_sig = False
    if ext == ".pdf" and header.startswith(MAGIC_NUMBERS["pdf"]):
        is_valid_sig = True
    elif ext in [".jpg", ".jpeg"] and header.startswith(MAGIC_NUMBERS["jpeg"]):
        is_valid_sig = True
    elif ext == ".png" and header.startswith(MAGIC_NUMBERS["png"]):
        is_valid_sig = True
    elif ext == ".webp" and header.startswith(MAGIC_NUMBERS["webp"]) and len(header) >= 12 and header[8:12] == b"WEBP":
        is_valid_sig = True

    if not is_valid_sig:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File binary signature mismatch for '{clean_base}'. The file content does not match the '{ext}' format."
        )

    # 3. Read the remainder of the stream while enforcing 5MB ceiling
    remaining = await file.read()
    total_bytes = header + remaining
    total_size = len(total_bytes)

    if total_size > MAX_KYC_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File '{clean_base}' ({total_size} bytes) exceeds the maximum permitted limit of 5MB ({MAX_KYC_FILE_SIZE} bytes)."
        )

    # 4. Cryptographic SHA-256 Digest
    sha256_hex = hashlib.sha256(total_bytes).hexdigest()

    # 5. Storage Strategy:
    # - Remote Vercel deployment -> Supabase Storage (private 'kyc-documents' bucket)
    # - Local running -> Local filesystem storage (uploads/kyc/{user_id}/)
    from core.config import settings
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    is_vercel = os.environ.get("VERCEL") == "1"
    force_supabase = os.environ.get("FORCE_SUPABASE_STORAGE", "false").lower() == "true"
    use_supabase = (is_vercel or force_supabase) and bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)

    if use_supabase:
        try:
            from infrastructure.storage.supabase_storage import supabase_storage
            await supabase_storage.ensure_bucket_exists("kyc-documents", is_public=False)
            object_key = f"{user_id}/{safe_filename}"
            mime_type = file.content_type or ("application/pdf" if ext == ".pdf" else f"image/{ext.lstrip('.')}")
            uploaded = await supabase_storage.upload_file(
                bucket_name="kyc-documents",
                object_path=object_key,
                content=total_bytes,
                mime_type=mime_type
            )
            if uploaded:
                return f"supabase://kyc-documents/{object_key}", clean_base, sha256_hex
        except Exception:
            pass  # Fall back to local storage if cloud upload encounters an issue

    # Local Storage (default for local running or fallback)
    storage_dir = os.path.join(settings.UPLOAD_DIR, "kyc", str(user_id))
    os.makedirs(storage_dir, exist_ok=True)
    dest_path = os.path.join(storage_dir, safe_filename)

    with open(dest_path, "wb") as out_f:
        out_f.write(total_bytes)

    # Store normalized path using forward slashes for cross-platform DB consistency
    normalized_path = dest_path.replace("\\", "/")
    return normalized_path, clean_base, sha256_hex
