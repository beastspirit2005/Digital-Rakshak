import uuid
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from domain.models.bank import (
    BankEscalation,
    BankRegistry,
    BankResponseActionType
)
from domain.services.bank_integrations.base_adapter import BaseBankAdapter

logger = logging.getLogger(__name__)


class SandboxBankAdapter(BaseBankAdapter):
    """
    Simulated Sandbox Adapter representing partner banks (SBI, HDFC, ICICI, Axis, PNB, etc.).
    Simulates wire latency, cryptographic HMAC-SHA256 signatures, and nodal acknowledgements.
    Enforces strict idempotency semantics: retries retain the parent's logical idempotency key.
    Includes failure injection support for scenario and resilience testing.
    """

    def __init__(self, simulate_failure: bool = False, fail_bank_codes: Optional[list] = None):
        self.simulate_failure = simulate_failure
        self.fail_bank_codes = set(fail_bank_codes or [])

    def sign_payload(self, payload: Dict[str, Any], secret_key: str = "dr_sandbox_secret") -> str:
        canonical_str = json.dumps(payload, sort_keys=True)
        return hmac.new(secret_key.encode(), canonical_str.encode(), hashlib.sha256).hexdigest()

    def verify_callback(
        self,
        payload_bytes: bytes,
        signature: str,
        timestamp_str: Optional[str] = None,
        secret_key: str = "dr_sandbox_secret"
    ) -> Tuple[bool, Optional[str]]:
        if timestamp_str:
            canonical = f"{timestamp_str}.{payload_bytes.decode('utf-8', errors='ignore')}"
            expected_sig = hmac.new(secret_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_sig, signature):
                return True, None
        
        # Fallback raw payload check
        simple_sig = hmac.new(secret_key.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if hmac.compare_digest(simple_sig, signature):
            return True, None

        return False, "Callback signature verification failed."

    async def submit_alert(self, escalation: BankEscalation, target_bank: BankRegistry) -> Dict[str, Any]:
        # Simulated failure injection check
        if self.simulate_failure or target_bank.bank_code in self.fail_bank_codes:
            raise ConnectionError(f"Simulated network timeout connecting to {target_bank.bank_name} nodal gateway.")

        sig = self.sign_payload(escalation.alert_payload)
        ack_ref = f"ACK-{target_bank.bank_code}-{uuid.uuid4().hex[:8].upper()}"

        # Distinct acknowledgement notes per instruction category
        if escalation.instruction_category == "STATUTORY_FREEZE_ORDER":
            initial_action = "Beneficiary account placed under immediate statutory debit freeze pursuant to Section 106 BNSS."
        elif escalation.instruction_category == "PROTECTIVE_HOLD_REQUEST":
            initial_action = "Precautionary debit lien / escrow hold placed on beneficiary account pending investigator confirmation."
        elif escalation.instruction_category == "RECORD_REQUEST_BNSS_94":
            initial_action = "Section 94 BNSS summons logged; nodal officer initiating KYC and IP transaction audit extraction."
        else:
            initial_action = (
                "Informational fraud alert acknowledged; remitter advised for credential reset."
                if escalation.escalation_role == "VICTIM_BANK"
                else "Informational alert acknowledged; beneficiary account flagged for rapid monitoring."
            )

        return {
            "success": True,
            "http_status_code": 202,
            "bank_reference": ack_ref,
            "response_type": BankResponseActionType.ACKNOWLEDGEMENT.value,
            "status_summary": f"Accepted by {target_bank.bank_name} Nodal Fraud Desk",
            "details": {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "signature_verified": True,
                "hmac_digest": sig[:16] + "...",
                "idempotency_key": escalation.idempotency_key,
                "statutory_basis": escalation.statutory_basis,
                "instruction_category": escalation.instruction_category,
                "initial_action": initial_action,
                "sla_note": "Internal sandbox acknowledgement (<500ms). Real bank SLA varies by institution rail."
            }
        }

    async def check_health(self, target_bank: BankRegistry) -> Dict[str, Any]:
        is_healthy = not (self.simulate_failure or target_bank.bank_code in self.fail_bank_codes)
        return {
            "bank_code": target_bank.bank_code,
            "bank_name": target_bank.bank_name,
            "is_reachable": is_healthy,
            "status": "HEALTHY" if is_healthy else "UNREACHABLE",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
