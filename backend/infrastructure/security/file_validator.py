import filetype
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

class FileValidator:
    """
    Strict Magic Byte validation for file uploads.
    Ensures that a file claiming to be a PDF is actually a PDF at the byte level,
    preventing polyglot attacks or reverse shell uploads disguised as images.
    """
    
    ALLOWED_MIMES = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "application/pdf": [".pdf"],
        "application/vnd.android.package-archive": [".apk"],
        "application/zip": [".apk", ".zip"], # Some APKs are parsed as standard ZIPs
        "application/java-archive": [".apk"]
    }
    
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    @classmethod
    def validate_file(cls, file_bytes: bytes, declared_extension: str) -> Tuple[bool, str]:
        """
        Returns (is_valid, error_message).
        """
        if len(file_bytes) > cls.MAX_FILE_SIZE_BYTES:
            return False, "File exceeds maximum allowed size of 50MB."
            
        kind = filetype.guess(file_bytes)
        
        if kind is None:
            return False, "Unable to determine file magic bytes. File may be corrupted or unsupported."
            
        mime_type = kind.mime
        
        if mime_type not in cls.ALLOWED_MIMES:
            logger.warning(f"Rejected file upload. Disallowed MIME type: {mime_type}")
            return False, f"Disallowed file signature detected: {mime_type}"
            
        allowed_extensions_for_mime = cls.ALLOWED_MIMES[mime_type]
        if declared_extension.lower() not in allowed_extensions_for_mime:
            logger.warning(f"File extension mismatch. MIME {mime_type} does not match extension {declared_extension}")
            return False, f"File extension {declared_extension} does not match its internal signature."
            
        return True, ""
