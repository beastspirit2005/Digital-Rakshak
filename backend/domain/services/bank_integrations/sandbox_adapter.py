import uuid
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

from domain.models.bank import (
    BankEscalation,
    BankRegistry,
    BankResponseActionType
)
from domain.services.bank_integrations.base_adapter import BaseBankAdapter
from services.mock_bank_service import mock_bank_service, SandboxScenario

logger = logging.getLogger(__name__)


class SandboxBankAdapter(BaseBankAdapter):
    """
    Simulated Sandbox Adapter representing partner banks (SBI, HDFC, ICICI, Axis, PNB, etc.).
    Simulates wire latency, cryptographic HMAC-SHA256 signatures, and nodal acknowledgements.
    Enforces strict receiver-side idempotency and supports dynamic failure injection scenarios.
    All outputs explicitly carry simulated sandbox indicators and legal disclaimers.
    """

    def __init__(self, simulate_failure: bool = False, fail_bank_codes: Optional[list] = None):
        self.simulate_failure = simulate_failure
        self.fail_bank_codes = set(fail_bank_codes or [])
        self.mock_service = mock_bank_service

    def set_scenario(self, scenario: str, bank_code: Optional[str] = None):
        """Switches simulation scenario on the mock bank receiver."""
        self.mock_service.set_scenario(scenario, bank_code=bank_code)

    def reset_store(self):
        """Clears the mock bank's receiver-side idempotency cache."""
        self.mock_service.reset()

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
        """
        Verifies cryptographic HMAC signature on bank callback.
        """
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
        """
        Submits alert to mock banking receiver under active failure injection scenario.
        Enforces receiver-side idempotency: retries retain the parent's logical idempotency key.
        """
        # Legacy flag check
        if self.simulate_failure or target_bank.bank_code in self.fail_bank_codes:
            raise ConnectionError(f"Simulated network timeout connecting to {target_bank.bank_name} nodal gateway.")

        # Extract transaction amount if available
        txn_amount = None
        if hasattr(escalation, "transaction") and escalation.transaction:
            txn_amount = escalation.transaction.amount

        # Dispatch to mock bank receiver
        result = self.mock_service.process_incoming_alert(
            bank_code=target_bank.bank_code,
            bank_name=target_bank.bank_name,
            idempotency_key=escalation.idempotency_key,
            alert_reference=escalation.alert_reference,
            instruction_category=escalation.instruction_category,
            escalation_role=escalation.escalation_role,
            amount=txn_amount
        )

        # Attach standard response fields if missing
        if "response_type" not in result:
            result["response_type"] = BankResponseActionType.ACKNOWLEDGEMENT.value
        if "bank_reference" not in result:
            result["bank_reference"] = f"ACK-{target_bank.bank_code}-{uuid.uuid4().hex[:8].upper()}"

        return result

    async def check_health(self, target_bank: BankRegistry) -> Dict[str, Any]:
        scenario = self.mock_service.get_scenario(target_bank.bank_code)
        is_healthy = scenario in (SandboxScenario.SUCCESS, SandboxScenario.DELAYED_ACK, SandboxScenario.PARTIAL_FREEZE)
        return {
            "bank_code": target_bank.bank_code,
            "bank_name": target_bank.bank_name,
            "is_reachable": is_healthy,
            "simulated_scenario": scenario,
            "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX"
        }
