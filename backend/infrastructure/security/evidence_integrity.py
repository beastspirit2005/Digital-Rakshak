import hashlib
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class EvidenceIntegrityPipeline:
    """
    Ensures that digital evidence remains untampered from the point of ingestion
    through the entire investigation lifecycle.
    """
    
    @staticmethod
    def calculate_sha256(file_bytes: bytes) -> str:
        """Calculates the SHA-256 hash of a byte array."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()
        
    @staticmethod
    def verify_integrity(file_bytes: bytes, expected_hash: str) -> Tuple[bool, str]:
        """
        Verifies that the provided file matches the expected SHA-256 hash.
        """
        actual_hash = EvidenceIntegrityPipeline.calculate_sha256(file_bytes)
        
        if actual_hash == expected_hash:
            return True, actual_hash
        else:
            logger.error(f"EVIDENCE INTEGRITY COMPROMISED! Expected: {expected_hash}, Actual: {actual_hash}")
            return False, actual_hash
