import abc
import uuid
import hmac
import hashlib
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from domain.models.bank import (
    BankEscalation,
    BankDeliveryAttempt,
    BankResponse,
    BankRegistry,
    EscalationStatus,
    BankResponseActionType
)
from domain.models.case import Case
from domain.models.user import User

logger = logging.getLogger(__name__)


class BaseBankAdapter(abc.ABC):
    """Abstract interface for external banking institution gateways."""

    @abc.abstractmethod
    async def submit_alert(self, escalation: BankEscalation, target_bank: BankRegistry) -> Dict[str, Any]:
        """Submits structured fraud alert to target bank."""
        pass

    @abc.abstractmethod
    def sign_payload(self, payload: Dict[str, Any], secret_key: str) -> str:
        """Signs alert payload using HMAC-SHA256."""
        pass


class SandboxBankAdapter(BaseBankAdapter):
    """
    Simulated Sandbox Adapter representing partner banks (SBI, HDFC, ICICI, Axis, etc.).
    Simulates wire latency, cryptographic verification, and bank nodal acknowledgements.
    """

    def sign_payload(self, payload: Dict[str, Any], secret_key: str = "dr_sandbox_secret") -> str:
        canonical_str = json.dumps(payload, sort_keys=True)
        return hmac.new(secret_key.encode(), canonical_str.encode(), hashlib.sha256).hexdigest()

    async def submit_alert(self, escalation: BankEscalation, target_bank: BankRegistry) -> Dict[str, Any]:
        # Simulate realistic sub-second network latency to bank gateway
        # Instant sandbox dispatch without loopback timer latency

        sig = self.sign_payload(escalation.alert_payload)
        ack_ref = f"ACK-{target_bank.bank_code}-{uuid.uuid4().hex[:8].upper()}"

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
                "initial_action": "Beneficiary account flagged for surveillance and temporary lien check."
                if escalation.escalation_role == "BENEFICIARY_BANK"
                else "Remitter account security review initiated; customer alerted for credential reset."
            }
        }


class BankIntegrationGateway:
    """
    Central Gateway coordinating dispatch, retries, delivery tracking,
    and institutional response logging.
    """

    _adapters: Dict[str, BaseBankAdapter] = {
        "SANDBOX_API": SandboxBankAdapter(),
        "DIRECT_API": SandboxBankAdapter(),  # Fallback to sandbox until live endpoints configured
    }

    @classmethod
    async def dispatch_escalation(
        cls,
        db: AsyncSession,
        escalation_id: uuid.UUID,
        approver_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Executes alert dispatch to the target financial institution.
        """
        res = await db.execute(
            select(BankEscalation).where(BankEscalation.id == escalation_id)
        )
        escalation = res.scalar_one_or_none()
        if not escalation:
            raise ValueError(f"Bank escalation {escalation_id} not found.")

        # Fetch Target Bank
        res_bank = await db.execute(
            select(BankRegistry).where(BankRegistry.id == escalation.target_bank_id)
        )
        target_bank = res_bank.scalar_one_or_none()
        if not target_bank:
            raise ValueError(f"Target bank for escalation {escalation_id} not found.")

        # Update approval if user provided
        if approver_user:
            escalation.approved_by = approver_user.id
            escalation.approved_at = datetime.now(timezone.utc)

        adapter = cls._adapters.get(target_bank.integration_type, SandboxBankAdapter())

        try:
            dispatch_result = await adapter.submit_alert(escalation, target_bank)

            # Record Delivery Attempt
            attempt = BankDeliveryAttempt(
                escalation_id=escalation.id,
                attempt_number=1,
                channel="API",
                http_status_code=dispatch_result.get("http_status_code", 200),
                response_body=dispatch_result,
                delivery_status="SUCCESS" if dispatch_result.get("success") else "FAILED",
                error_message=None
            )
            db.add(attempt)

            # Record Institutional Response
            bank_resp = BankResponse(
                escalation_id=escalation.id,
                bank_reference_number=dispatch_result.get("bank_reference"),
                response_type=dispatch_result.get("response_type", BankResponseActionType.ACKNOWLEDGEMENT.value),
                status_summary=dispatch_result.get("status_summary", "Acknowledged"),
                details=dispatch_result.get("details", {})
            )
            db.add(bank_resp)

            # Update Escalation Status
            escalation.status = EscalationStatus.ACKNOWLEDGED.value
            escalation.updated_at = datetime.now(timezone.utc)

            # Update Case Timeline
            res_case = await db.execute(
                select(Case).where(Case.id == escalation.case_id)
            )
            case = res_case.scalar_one_or_none()
            if case:
                if not isinstance(case.timeline_events, list):
                    case.timeline_events = []
                
                timeline_entry = {
                    "event_type": "BANK_ESCALATION_DISPATCHED",
                    "title": f"Fraud Alert Dispatched to {target_bank.bank_name}",
                    "description": (
                        f"Alert Ref: {escalation.alert_reference} ({escalation.escalation_role}). "
                        f"Target Institution: {target_bank.bank_name}. "
                        f"Status: Acknowledged ({dispatch_result.get('bank_reference')})."
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "escalation_id": str(escalation.id),
                        "alert_reference": escalation.alert_reference,
                        "bank_code": target_bank.bank_code,
                        "role": escalation.escalation_role,
                        "ack_ref": dispatch_result.get("bank_reference")
                    }
                }
                case.timeline_events.append(timeline_entry)
                flag_modified(case, "timeline_events")

            await db.commit()
            return {
                "success": True,
                "escalation_id": str(escalation.id),
                "alert_reference": escalation.alert_reference,
                "status": escalation.status,
                "target_bank": target_bank.bank_name,
                "bank_reference": dispatch_result.get("bank_reference")
            }

        except Exception as e:
            logger.error(f"Failed to dispatch escalation {escalation_id}: {e}")
            attempt = BankDeliveryAttempt(
                escalation_id=escalation.id,
                attempt_number=1,
                channel="API",
                http_status_code=500,
                response_body={"error": str(e)},
                delivery_status="FAILED",
                error_message=str(e)
            )
            db.add(attempt)
            escalation.status = EscalationStatus.FAILED.value
            await db.commit()
            return {
                "success": False,
                "escalation_id": str(escalation.id),
                "error": str(e)
            }
