import abc
from typing import Dict, Any, Optional, Tuple
from domain.models.bank import BankEscalation, BankRegistry


class BaseBankAdapter(abc.ABC):
    """
    Standardized Abstract Interface for Institutional Bank Integrations.
    Guarantees consistent contracts across sandbox, REST, SFTP, and SFMS/NEFT rails.
    """

    @abc.abstractmethod
    async def submit_alert(self, escalation: BankEscalation, target_bank: BankRegistry) -> Dict[str, Any]:
        """Submits structured fraud alert to target institution."""
        pass

    @abc.abstractmethod
    def sign_payload(self, payload: Dict[str, Any], secret_key: str) -> str:
        """Signs alert payload using cryptographic signature (e.g. HMAC-SHA256)."""
        pass

    @abc.abstractmethod
    def verify_callback(
        self,
        payload_bytes: bytes,
        signature: str,
        timestamp_str: Optional[str] = None,
        secret_key: str = "dr_sandbox_secret"
    ) -> Tuple[bool, Optional[str]]:
        """Verifies incoming callback authenticity, signature, and timestamp replay."""
        pass

    @abc.abstractmethod
    async def check_health(self, target_bank: BankRegistry) -> Dict[str, Any]:
        """Probes institution endpoint health and connectivity."""
        pass
