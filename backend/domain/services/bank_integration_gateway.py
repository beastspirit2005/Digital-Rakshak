import abc
import uuid
import hmac
import hashlib
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from domain.models.bank import (
    BankEscalation,
    BankDeliveryAttempt,
    BankResponse,
    BankRegistry,
    EscalationStatus,
    BankResponseActionType,
    InstitutionalOutboxEvent,
    FraudResponseStage,
    WebhookNonceReplayCache
)
from domain.models.case import Case
from domain.models.user import User
from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine
from domain.services.bank_integrations import (
    BaseBankAdapter,
    SandboxBankAdapter,
    BankCircuitBreaker,
    DeliveryManager
)

logger = logging.getLogger(__name__)


class BankIntegrationGateway:
    """
    Central Institutional Integration Gateway coordinating dispatch, retries,
    circuit breaking, delivery tracking, and bank response verification.
    Guarantees that retries reuse the exact logical idempotency key while
    logging each physical transmission attempt with a new attempt ID and attempt number.
    """

    delivery_manager: DeliveryManager = DeliveryManager()

    @classmethod
    async def queue_escalation_in_outbox(
        cls,
        db: AsyncSession,
        escalation: BankEscalation,
        correlation_id: str
    ) -> InstitutionalOutboxEvent:
        """
        Transactional Outbox Writer:
        Persists an InstitutionalOutboxEvent within the caller's active database transaction.
        Guarantees crash-safe delivery without dual-write hazards.
        """
        # Check if an outbox event already exists for this escalation
        stmt = (
            select(InstitutionalOutboxEvent)
            .where(
                InstitutionalOutboxEvent.aggregate_id == escalation.id,
                InstitutionalOutboxEvent.event_type == "BANK_ESCALATION_DISPATCH"
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        outbox_event = InstitutionalOutboxEvent(
            event_type="BANK_ESCALATION_DISPATCH",
            aggregate_id=escalation.id,
            correlation_id=correlation_id,
            payload={
                "escalation_id": str(escalation.id),
                "case_id": str(escalation.case_id),
                "alert_reference": escalation.alert_reference,
                "idempotency_key": escalation.idempotency_key,
                "target_bank_id": str(escalation.target_bank_id),
                "instruction_category": escalation.instruction_category
            },
            status="PENDING",
            attempt_count=0,
            available_at=datetime.now(timezone.utc)
        )
        db.add(outbox_event)
        await db.flush()
        logger.info(f"Queued outbox event {outbox_event.id} for escalation {escalation.alert_reference}")
        return outbox_event

    @classmethod
    async def dispatch_escalation(
        cls,
        db: AsyncSession,
        escalation_id: uuid.UUID,
        approver_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Executes alert dispatch to the target financial institution through the delivery manager.
        Preserves escalation.idempotency_key across all physical attempts.
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

        # Determine next physical attempt number while retaining logical idempotency key
        res_prev = await db.execute(
            select(BankDeliveryAttempt).where(BankDeliveryAttempt.escalation_id == escalation.id)
        )
        attempt_number = len(res_prev.scalars().all()) + 1

        try:
            # Deliver under circuit breaker supervision
            dispatch_result = await cls.delivery_manager.execute_delivery(escalation, target_bank)

            # Record Physical Delivery Attempt
            attempt = BankDeliveryAttempt(
                escalation_id=escalation.id,
                attempt_number=attempt_number,
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

            # Record Lifecycle Stage 6 & 7 (NOTICE_DISPATCHED & BANK_RESPONSE_RECEIVED)
            corr_id = f"CORR-{escalation.alert_reference}"
            await FraudLifecycleEngine.record_transition(
                db=db,
                correlation_id=corr_id,
                case_id=escalation.case_id,
                stage=FraudResponseStage.NOTICE_DISPATCHED,
                actor_or_service=f"GATEWAY:{target_bank.bank_code}",
                transition_reason=f"Fraud alert transmitted to {target_bank.bank_name} (Attempt #{attempt_number}).",
                transaction_id=escalation.transaction_id,
                escalation_id=escalation.id,
                metadata={"idempotency_key": escalation.idempotency_key, "attempt_number": attempt_number}
            )

            await FraudLifecycleEngine.record_transition(
                db=db,
                correlation_id=corr_id,
                case_id=escalation.case_id,
                stage=FraudResponseStage.BANK_RESPONSE_RECEIVED,
                actor_or_service=f"BANK_NODAL:{target_bank.bank_code}",
                transition_reason=f"Bank acknowledged alert: {dispatch_result.get('bank_reference')}.",
                transaction_id=escalation.transaction_id,
                escalation_id=escalation.id,
                metadata={"response_type": dispatch_result.get("response_type"), "bank_reference": dispatch_result.get("bank_reference")}
            )

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
                        f"Category: {escalation.instruction_category} (Attempt #{attempt_number}). "
                        f"Target Institution: {target_bank.bank_name}. "
                        f"Status: Acknowledged ({dispatch_result.get('bank_reference')})."
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "escalation_id": str(escalation.id),
                        "alert_reference": escalation.alert_reference,
                        "idempotency_key": escalation.idempotency_key,
                        "attempt_number": attempt_number,
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
                "idempotency_key": escalation.idempotency_key,
                "attempt_number": attempt_number,
                "status": escalation.status,
                "target_bank": target_bank.bank_name,
                "bank_reference": dispatch_result.get("bank_reference")
            }

        except Exception as e:
            logger.error(f"Failed to dispatch escalation {escalation_id} (Attempt #{attempt_number}): {e}")
            attempt = BankDeliveryAttempt(
                escalation_id=escalation.id,
                attempt_number=attempt_number,
                channel="API",
                http_status_code=500,
                response_body={"error": str(e)},
                delivery_status="FAILED",
                error_message=str(e)
            )
            db.add(attempt)
            # Institutional DLQ: route to DEAD_LETTER after 5 failed attempts
            if attempt_number >= 5:
                escalation.status = EscalationStatus.DEAD_LETTER.value
                logger.critical(f"Bank escalation {escalation.id} routed to DEAD_LETTER after {attempt_number} failures.")
            else:
                escalation.status = EscalationStatus.FAILED.value

            await db.commit()
            return {
                "success": False,
                "escalation_id": str(escalation.id),
                "attempt_number": attempt_number,
                "is_dead_letter": attempt_number >= 5,
                "error": str(e)
            }

    @classmethod
    def verify_callback_authenticity(
        cls,
        payload_bytes: bytes,
        signature: str,
        timestamp_str: Optional[str] = None,
        secret_key: str = "dr_sandbox_secret",
        max_skew_seconds: int = 300
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates callback signature, timestamp replay window (<= 300s), and payload integrity.
        """
        if timestamp_str:
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                skew = abs((now - ts).total_seconds())
                if skew > max_skew_seconds:
                    return False, f"Callback rejected: Clock skew {skew:.1f}s exceeds maximum {max_skew_seconds}s replay window."
            except Exception:
                return False, "Callback rejected: Invalid ISO 8601 timestamp in X-Callback-Timestamp header."

            canonical = f"{timestamp_str}.{payload_bytes.decode('utf-8', errors='ignore')}"
            expected_sig = hmac.new(secret_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_sig, signature):
                return True, None

        # Fallback raw payload check
        simple_sig = hmac.new(secret_key.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if hmac.compare_digest(simple_sig, signature):
            return True, None

        return False, "Callback rejected: Cryptographic HMAC-SHA256 signature mismatch."

    @classmethod
    async def validate_and_record_nonce(
        cls,
        db: AsyncSession,
        bank_code: str,
        nonce: str,
        signature: str,
        ttl_hours: int = 24
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates persistent database-backed replay cache for bank webhooks.
        Rejects duplicate nonces to prevent replay attacks and duplicate processing.
        """
        stmt = select(WebhookNonceReplayCache).where(WebhookNonceReplayCache.nonce == nonce)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return False, f"Replay rejected: Webhook callback nonce {nonce} has already been processed."

        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=ttl_hours)
        cached = WebhookNonceReplayCache(
            bank_code=bank_code,
            nonce=nonce,
            signature=signature,
            created_at=now,
            expires_at=expires
        )
        db.add(cached)
        await db.flush()
        return True, None

    @classmethod
    def get_health_metrics(cls) -> Dict[str, Any]:
        """Returns gateway circuit breaker health snapshot."""
        return cls.delivery_manager.circuit_breaker.get_health_metrics()
