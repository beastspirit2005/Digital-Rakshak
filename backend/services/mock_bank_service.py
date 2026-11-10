import uuid
import hmac
import hashlib
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List, Union
from decimal import Decimal

logger = logging.getLogger(__name__)


class SandboxScenario:
    SUCCESS = "SUCCESS"
    DELAYED_ACK = "DELAYED_ACK"
    RATE_LIMITED_429 = "RATE_LIMITED_429"
    SERVER_ERROR_500 = "SERVER_ERROR_500"
    TIMEOUT_504 = "TIMEOUT_504"
    CONNECTION_RESET = "CONNECTION_RESET"
    INVALID_AUTH = "INVALID_AUTH"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    CONFLICTING_FINANCIAL = "CONFLICTING_FINANCIAL"
    PARTIAL_FREEZE = "PARTIAL_FREEZE"


class MockBankReceiverStore:
    """
    Independent Receiver-Side Idempotency Store:
    Simulates partner bank core-banking receiving ledger.
    Guarantees that retries bearing identical idempotency keys return the
    cached action without executing duplicate debits, liens, or freeze actions.
    """

    def __init__(self):
        # Key: idempotency_key -> { bank_reference, response_payload, request_count, first_received_at }
        self._received_requests: Dict[str, Dict[str, Any]] = {}
        # Key: nonce -> timestamp
        self._callback_nonces: Dict[str, float] = {}
        # Per-bank scenario configuration: bank_code -> scenario
        self._scenarios: Dict[str, str] = {}
        self._default_scenario = SandboxScenario.SUCCESS
        self.secret_key = "dr_sandbox_secret"

    def set_scenario(self, scenario: str, bank_code: Optional[str] = None):
        """Sets simulation scenario globally or per bank code."""
        if bank_code:
            self._scenarios[bank_code.upper()] = scenario
        else:
            self._default_scenario = scenario

    def get_scenario(self, bank_code: Optional[str] = None) -> str:
        """Gets active scenario for bank code, falling back to default."""
        if bank_code and bank_code.upper() in self._scenarios:
            return self._scenarios[bank_code.upper()]
        return self._default_scenario

    def reset(self):
        """Resets receiver store and scenarios."""
        self._received_requests.clear()
        self._callback_nonces.clear()
        self._scenarios.clear()
        self._default_scenario = SandboxScenario.SUCCESS

    def sign_payload(self, payload: Union[Dict[str, Any], str]) -> str:
        """Generates canonical HMAC-SHA256 signature for bank payloads."""
        if isinstance(payload, str):
            canonical_str = payload
        else:
            canonical_str = json.dumps(payload, sort_keys=True)
        return hmac.new(self.secret_key.encode(), canonical_str.encode(), hashlib.sha256).hexdigest()

    def process_incoming_alert(
        self,
        bank_code: str,
        bank_name: str,
        idempotency_key: str,
        alert_reference: str,
        instruction_category: str,
        escalation_role: str,
        amount: Optional[Decimal] = None,
        auth_header: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes alert receipt on the mock bank side, evaluating active failure scenarios
        and enforcing strict receiver-side idempotency.
        """
        scenario = self.get_scenario(bank_code)

        # 1. Invalid Authentication Simulation
        if scenario == SandboxScenario.INVALID_AUTH:
            logger.warning(f"[MOCK_BANK:{bank_code}] Rejecting alert with 401 Unauthorized.")
            raise PermissionError("401 Unauthorized: Nodal API credentials rejected by partner core system.")

        # 2. Rate Limiting Simulation (HTTP 429)
        if scenario == SandboxScenario.RATE_LIMITED_429:
            logger.warning(f"[MOCK_BANK:{bank_code}] Rejecting alert with 429 Rate Limit Exceeded.")
            raise ConnectionRefusedError("429 Too Many Requests: Rate limit exceeded. Retry-After: 60s.")

        # 3. Server Error Simulation (HTTP 500)
        if scenario == SandboxScenario.SERVER_ERROR_500:
            logger.warning(f"[MOCK_BANK:{bank_code}] Failing alert with 500 Core Banking Error.")
            raise RuntimeError("500 Internal Server Error: Core banking database deadlock.")

        # 4. Connection Timeout Simulation (HTTP 504)
        if scenario == SandboxScenario.TIMEOUT_504:
            logger.warning(f"[MOCK_BANK:{bank_code}] Simulating 504 Gateway Timeout.")
            raise TimeoutError("504 Gateway Timeout: Bank switchboard did not respond within wire SLA.")

        # 5. Connection Reset Simulation
        if scenario == SandboxScenario.CONNECTION_RESET:
            logger.warning(f"[MOCK_BANK:{bank_code}] Simulating TCP Connection Reset.")
            raise ConnectionResetError("Connection reset by peer during TLS handshake with bank gateway.")

        # 6. Receiver-Side Idempotency Check
        if idempotency_key in self._received_requests:
            existing = self._received_requests[idempotency_key]
            existing["request_count"] += 1
            existing["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(
                f"[MOCK_BANK:{bank_code}] Duplicate dispatch detected for idempotency_key: {idempotency_key}. "
                f"Returning cached acknowledgement (Attempt #{existing['request_count']}). Zero double action."
            )
            # Return cached response with identical bank_reference
            cached_resp = dict(existing["response_payload"])
            cached_resp["details"]["is_duplicate"] = True
            cached_resp["details"]["attempt_count"] = existing["request_count"]
            return cached_resp

        # 7. Malformed Response Simulation
        if scenario == SandboxScenario.MALFORMED_RESPONSE:
            logger.warning(f"[MOCK_BANK:{bank_code}] Emitting malformed response payload.")
            return {
                "corrupted_raw_bytes": "0xDEADBEEF_CORRUPTED_XML_FRAGMENT",
                "missing_required_keys": True
            }

        # 8. Conflicting Financial Response Simulation (Frozen > Original Amount)
        if scenario == SandboxScenario.CONFLICTING_FINANCIAL:
            orig = amount or Decimal("10000.00")
            conflicting_frozen = orig * Decimal("2.5") # Illegal: frozen > original
            ack_ref = f"ACK-CONFLICT-{bank_code}-{uuid.uuid4().hex[:8].upper()}"
            resp = {
                "success": True,
                "http_status_code": 200,
                "bank_reference": ack_ref,
                "response_type": "ACTION_TAKEN",
                "status_summary": f"Conflicting response from {bank_name}",
                "funds_frozen_amount": float(conflicting_frozen),
                "details": {
                    "scenario": SandboxScenario.CONFLICTING_FINANCIAL,
                    "illegal_frozen_amount": float(conflicting_frozen),
                    "original_amount": float(orig),
                    "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX"
                }
            }
            self._received_requests[idempotency_key] = {
                "bank_reference": ack_ref,
                "response_payload": resp,
                "request_count": 1,
                "first_received_at": datetime.now(timezone.utc).isoformat()
            }
            return resp

        # 9. Partial Freeze Simulation ($F < P$)
        if scenario == SandboxScenario.PARTIAL_FREEZE:
            orig = amount or Decimal("50000.00")
            partial = orig * Decimal("0.40") # 40% secured
            ack_ref = f"ACK-PARTIAL-{bank_code}-{uuid.uuid4().hex[:8].upper()}"
            resp = {
                "success": True,
                "http_status_code": 200,
                "bank_reference": ack_ref,
                "response_type": "ACTION_TAKEN",
                "status_summary": f"Partial debit hold executed by {bank_name}",
                "funds_frozen_amount": float(partial),
                "details": {
                    "scenario": SandboxScenario.PARTIAL_FREEZE,
                    "frozen_amount": float(partial),
                    "original_amount": float(orig),
                    "shortfall_reason": "Insufficient ledger balance in beneficiary account",
                    "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX"
                }
            }
            self._received_requests[idempotency_key] = {
                "bank_reference": ack_ref,
                "response_payload": resp,
                "request_count": 1,
                "first_received_at": datetime.now(timezone.utc).isoformat()
            }
            return resp

        # 10. Standard Successful Acknowledgement (Default)
        ack_ref = f"ACK-{bank_code}-{uuid.uuid4().hex[:8].upper()}"
        initial_action = (
            "Beneficiary account placed under immediate statutory debit freeze pursuant to Section 106 BNSS."
            if instruction_category == "STATUTORY_FREEZE_ORDER"
            else "Precautionary debit lien placed on beneficiary account pending inquiry."
            if instruction_category == "PROTECTIVE_HOLD_REQUEST"
            else "Informational fraud alert acknowledged by nodal fraud desk."
        )

        response_payload = {
            "success": True,
            "http_status_code": 202,
            "bank_reference": ack_ref,
            "response_type": "ACKNOWLEDGEMENT",
            "status_summary": f"Accepted by {bank_name} Nodal Fraud Desk",
            "details": {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": idempotency_key,
                "alert_reference": alert_reference,
                "instruction_category": instruction_category,
                "initial_action": initial_action,
                "is_duplicate": False,
                "attempt_count": 1,
                "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX",
                "disclaimer": "Simulated banking rail under BSA 2023 testing provisions. NOT a live core-banking or NPCI connection."
            }
        }

        # Cache in receiver-side idempotency store
        self._received_requests[idempotency_key] = {
            "bank_reference": ack_ref,
            "response_payload": response_payload,
            "request_count": 1,
            "first_received_at": datetime.now(timezone.utc).isoformat()
        }

        return response_payload

    def verify_and_record_callback(
        self,
        bank_code: str,
        nonce: str,
        payload_bytes: bytes,
        signature: str,
        timestamp_str: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates incoming bank callback webhook:
        1. Checks timestamp skew (maximum 300 seconds).
        2. Validates HMAC-SHA256 signature against canonical bytes.
        3. Enforces nonce replay prevention.
        """
        now = time.time()

        # 1. Timestamp validation (replay & skew check)
        if timestamp_str:
            try:
                cb_time = float(timestamp_str)
                skew = abs(now - cb_time)
                if skew > 300.0:
                    return False, f"Callback rejected: Clock skew {skew:.1f}s exceeds maximum permitted 300s window."
            except ValueError:
                return False, "Callback rejected: Malformed timestamp header."

        # 2. Nonce replay prevention
        if nonce in self._callback_nonces:
            return False, f"Callback rejected: Nonce {nonce} has already been processed (replay detected)."

        # 3. Signature verification
        canonical = f"{timestamp_str}.{payload_bytes.decode('utf-8', errors='ignore')}" if timestamp_str else payload_bytes.decode('utf-8', errors='ignore')
        expected_sig = hmac.new(self.secret_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return False, "Callback rejected: Cryptographic HMAC-SHA256 signature verification failed."

        # Record nonce in replay cache
        self._callback_nonces[nonce] = now
        return True, None

    def get_idempotency_store_dump(self) -> Dict[str, Any]:
        """Dumps internal idempotency store for verification in contract tests."""
        return {
            "total_keys": len(self._received_requests),
            "keys": list(self._received_requests.keys()),
            "requests": self._received_requests,
            "active_scenarios": self._scenarios,
            "default_scenario": self._default_scenario
        }


# Global singleton instance for sandbox testing and runtime simulation
mock_bank_service = MockBankReceiverStore()
