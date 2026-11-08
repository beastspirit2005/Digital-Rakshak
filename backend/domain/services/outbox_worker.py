import uuid
import logging
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from domain.models.bank import (
    InstitutionalOutboxEvent,
    BankEscalation,
    EscalationStatus
)
from domain.services.bank_integration_gateway import BankIntegrationGateway

logger = logging.getLogger(__name__)

RETRY_SCHEDULE_SECONDS = {
    1: 5,
    2: 15,
    3: 45,
    4: 120,
    5: 300
}
MAX_DISPATCH_ATTEMPTS = 5


class OutboxWorker:
    """
    Resilient Background Dispatch Worker implementing the Transactional Outbox Pattern.
    Claims pending institutional events atomically (using SKIP LOCKED),
    executes dispatches via the Bank Integration Gateway, applies exponential backoff with jitter,
    and routes permanently exhausted events to DEAD_LETTER.
    """

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"WORKER-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    def calculate_backoff(cls, attempt_count: int) -> int:
        """Calculates backoff delay in seconds with uniform +/- 10% jitter."""
        base = RETRY_SCHEDULE_SECONDS.get(attempt_count, 300)
        # Uniform jitter between 90% and 110%
        jitter_factor = random.uniform(0.9, 1.1)
        return max(1, int(base * jitter_factor))

    async def claim_batch(
        self,
        db: AsyncSession,
        batch_size: int = 10
    ) -> List[InstitutionalOutboxEvent]:
        """
        Atomically claims up to batch_size pending outbox events using FOR UPDATE SKIP LOCKED.
        Prevents concurrent workers from processing the same event.
        """
        now = datetime.now(timezone.utc)
        
        # Build query
        stmt = (
            select(InstitutionalOutboxEvent)
            .where(
                and_(
                    InstitutionalOutboxEvent.status == "PENDING",
                    InstitutionalOutboxEvent.available_at <= now
                )
            )
            .order_by(InstitutionalOutboxEvent.available_at.asc())
            .limit(batch_size)
        )

        # Apply SKIP LOCKED if supported (PostgreSQL), fallback for SQLite testing
        try:
            stmt = stmt.with_for_update(skip_locked=True)
            res = await db.execute(stmt)
            events = res.scalars().all()
        except Exception:
            # Fallback (e.g. SQLite dialect during unit testing)
            res = await db.execute(
                select(InstitutionalOutboxEvent)
                .where(
                    and_(
                        InstitutionalOutboxEvent.status == "PENDING",
                        InstitutionalOutboxEvent.available_at <= now
                    )
                )
                .order_by(InstitutionalOutboxEvent.available_at.asc())
                .limit(batch_size)
            )
            events = res.scalars().all()

        claimed_events = []
        for ev in events:
            ev.status = "PROCESSING"
            ev.locked_at = now
            ev.locked_by = self.worker_id
            claimed_events.append(ev)

        if claimed_events:
            await db.commit()
            logger.info(f"[{self.worker_id}] Atomically claimed {len(claimed_events)} outbox events.")

        return claimed_events

    async def process_event(
        self,
        db: AsyncSession,
        event: InstitutionalOutboxEvent
    ) -> Dict[str, Any]:
        """
        Executes dispatch of a single outbox event.
        Updates status, retries with backoff on failure, or moves to DEAD_LETTER.
        """
        logger.info(f"[{self.worker_id}] Processing outbox event {event.id} (aggregate: {event.aggregate_id})")

        try:
            # Aggregate ID corresponds to bank_escalation.id
            escalation_id = event.aggregate_id
            dispatch_res = await BankIntegrationGateway.dispatch_escalation(
                db=db,
                escalation_id=escalation_id
            )

            if dispatch_res.get("success"):
                event.status = "COMPLETED"
                event.processed_at = datetime.now(timezone.utc)
                event.last_error = None
                await db.commit()
                logger.info(f"[{self.worker_id}] Successfully dispatched outbox event {event.id}.")
                return {"success": True, "event_id": str(event.id), "dispatch_result": dispatch_res}
            else:
                err_msg = dispatch_res.get("error", "Dispatch unsuccessful")
                return await self._handle_failure(db, event, err_msg)

        except Exception as e:
            logger.error(f"[{self.worker_id}] Unexpected error processing outbox event {event.id}: {e}")
            return await self._handle_failure(db, event, str(e))

    async def _handle_failure(
        self,
        db: AsyncSession,
        event: InstitutionalOutboxEvent,
        error_msg: str
    ) -> Dict[str, Any]:
        """Handles failure, retry scheduling, or dead-letter queue routing."""
        event.attempt_count += 1
        event.last_error = error_msg
        now = datetime.now(timezone.utc)

        if event.attempt_count >= MAX_DISPATCH_ATTEMPTS:
            event.status = "DEAD_LETTER"
            event.processed_at = now
            logger.critical(
                f"[{self.worker_id}] Outbox event {event.id} routed to DEAD_LETTER "
                f"after {event.attempt_count} attempts. Reason: {error_msg}"
            )
            # Synchronize escalation status to DEAD_LETTER as well
            res_esc = await db.execute(
                select(BankEscalation).where(BankEscalation.id == event.aggregate_id)
            )
            esc = res_esc.scalar_one_or_none()
            if esc:
                esc.status = EscalationStatus.DEAD_LETTER.value
        else:
            delay_sec = self.calculate_backoff(event.attempt_count)
            event.status = "PENDING"
            event.available_at = now + timedelta(seconds=delay_sec)
            event.locked_at = None
            event.locked_by = None
            logger.warning(
                f"[{self.worker_id}] Outbox event {event.id} failed (attempt {event.attempt_count}/{MAX_DISPATCH_ATTEMPTS}). "
                f"Scheduled retry in {delay_sec}s."
            )

        await db.commit()
        return {
            "success": False,
            "event_id": str(event.id),
            "attempt_count": event.attempt_count,
            "is_dead_letter": event.status == "DEAD_LETTER",
            "error": error_msg
        }

    async def run_tick(self, db: AsyncSession, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Executes a single polling tick: claims pending events and processes them."""
        events = await self.claim_batch(db, batch_size=batch_size)
        results = []
        for ev in events:
            res = await self.process_event(db, ev)
            results.append(res)
        return results

    @classmethod
    async def get_queue_metrics(cls, db: AsyncSession) -> Dict[str, Any]:
        """Returns real-time queue health and outbox metrics."""
        now = datetime.now(timezone.utc)
        
        # Aggregate counts by status
        stmt = (
            select(InstitutionalOutboxEvent.status, func.count(InstitutionalOutboxEvent.id))
            .group_by(InstitutionalOutboxEvent.status)
        )
        res = await db.execute(stmt)
        status_counts = dict(res.all())

        # Pending ready vs pending scheduled in future
        stmt_ready = select(func.count(InstitutionalOutboxEvent.id)).where(
            and_(
                InstitutionalOutboxEvent.status == "PENDING",
                InstitutionalOutboxEvent.available_at <= now
            )
        )
        res_ready = await db.execute(stmt_ready)
        pending_ready = res_ready.scalar_one()

        return {
            "queue_depth": status_counts.get("PENDING", 0) + status_counts.get("PROCESSING", 0),
            "pending_ready": pending_ready,
            "pending_scheduled": status_counts.get("PENDING", 0) - pending_ready,
            "processing": status_counts.get("PROCESSING", 0),
            "completed": status_counts.get("COMPLETED", 0),
            "failed": status_counts.get("FAILED", 0),
            "dead_letter": status_counts.get("DEAD_LETTER", 0),
            "timestamp": now.isoformat()
        }
