import uuid
import logging
import asyncio
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from domain.models.bank import (
    InstitutionalOutboxEvent,
    OutboxWorkerRun,
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
    Claims pending and retry-scheduled events atomically (using SKIP LOCKED),
    recovers expired leases from crashed or timed-out workers,
    executes dispatches via the Bank Integration Gateway,
    applies exponential backoff with uniform jitter,
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

    async def recover_expired_leases(
        self,
        db: AsyncSession,
        now: Optional[datetime] = None
    ) -> int:
        """
        Identifies events held in 'PROCESSING' whose worker lease has expired,
        and transitions them to 'RETRY_SCHEDULED' so they can be re-claimed.
        Prevents zombie locks caused by serverless function timeouts or crashes.
        """
        now = now or datetime.now(timezone.utc)
        stmt = (
            select(InstitutionalOutboxEvent)
            .where(
                and_(
                    InstitutionalOutboxEvent.status == "PROCESSING",
                    InstitutionalOutboxEvent.lease_expires_at.isnot(None),
                    InstitutionalOutboxEvent.lease_expires_at < now
                )
            )
            .limit(25)
        )

        try:
            res = await db.execute(stmt.with_for_update(skip_locked=True))
            expired = res.scalars().all()
        except Exception:
            res = await db.execute(stmt)
            expired = res.scalars().all()

        for ev in expired:
            logger.warning(
                f"[{self.worker_id}] Recovering expired lease on event {ev.id} "
                f"(locked by: {ev.locked_by}, expired at: {ev.lease_expires_at})"
            )
            ev.status = "RETRY_SCHEDULED"
            ev.available_at = now
            ev.locked_by = None
            ev.lease_expires_at = None
            ev.last_error_code = "LEASE_EXPIRED_RECOVERED"

        if expired:
            await db.commit()
            logger.info(f"[{self.worker_id}] Successfully recovered {len(expired)} expired outbox leases.")

        return len(expired)

    async def claim_batch(
        self,
        db: AsyncSession,
        batch_size: int = 10,
        lease_seconds: int = 30
    ) -> List[InstitutionalOutboxEvent]:
        """
        Atomically claims up to batch_size pending or retry-eligible outbox events
        using FOR UPDATE SKIP LOCKED. Enforces lease expiration to prevent zombie locks.
        """
        now = datetime.now(timezone.utc)

        # 1. Recover any expired leases first
        await self.recover_expired_leases(db, now=now)

        # 2. Build claim query for eligible events
        stmt = (
            select(InstitutionalOutboxEvent)
            .where(
                and_(
                    InstitutionalOutboxEvent.status.in_(["PENDING", "RETRY_SCHEDULED"]),
                    InstitutionalOutboxEvent.available_at <= now
                )
            )
            .order_by(InstitutionalOutboxEvent.available_at.asc())
            .limit(batch_size)
        )

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
                        InstitutionalOutboxEvent.status.in_(["PENDING", "RETRY_SCHEDULED"]),
                        InstitutionalOutboxEvent.available_at <= now
                    )
                )
                .order_by(InstitutionalOutboxEvent.available_at.asc())
                .limit(batch_size)
            )
            events = res.scalars().all()

        claimed_events = []
        lease_expiry = now + timedelta(seconds=lease_seconds)

        for ev in events:
            ev.status = "PROCESSING"
            ev.locked_at = now
            ev.locked_by = self.worker_id
            ev.lease_expires_at = lease_expiry
            claimed_events.append(ev)

        if claimed_events:
            await db.commit()
            logger.info(
                f"[{self.worker_id}] Atomically claimed {len(claimed_events)} outbox events "
                f"with {lease_seconds}s lease expiry ({lease_expiry.isoformat()})."
            )

        return claimed_events

    async def process_event(
        self,
        db: AsyncSession,
        event: InstitutionalOutboxEvent
    ) -> Dict[str, Any]:
        """
        Executes dispatch of a single claimed outbox event.
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
                event.last_error_code = None
                event.lease_expires_at = None
                await db.commit()
                logger.info(f"[{self.worker_id}] Successfully dispatched outbox event {event.id}.")
                return {"success": True, "event_id": str(event.id), "dispatch_result": dispatch_res}
            else:
                err_msg = dispatch_res.get("error", "Dispatch unsuccessful")
                err_code = dispatch_res.get("error_code", "DISPATCH_FAILED")
                return await self._handle_failure(db, event, err_msg, error_code=err_code)

        except Exception as e:
            logger.error(f"[{self.worker_id}] Unexpected error processing outbox event {event.id}: {e}")
            return await self._handle_failure(db, event, str(e), error_code="UNEXPECTED_EXCEPTION")

    async def _handle_failure(
        self,
        db: AsyncSession,
        event: InstitutionalOutboxEvent,
        error_msg: str,
        error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handles failure, retry scheduling, or dead-letter queue routing."""
        event.attempt_count += 1
        event.last_error = error_msg
        event.last_error_code = error_code or "DISPATCH_FAILED"
        now = datetime.now(timezone.utc)

        if event.attempt_count >= MAX_DISPATCH_ATTEMPTS:
            event.status = "DEAD_LETTER"
            event.last_error_code = "MAX_ATTEMPTS_EXHAUSTED"
            event.processed_at = now
            event.lease_expires_at = None
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
            event.status = "RETRY_SCHEDULED"
            event.available_at = now + timedelta(seconds=delay_sec)
            event.locked_at = None
            event.locked_by = None
            event.lease_expires_at = None
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
            "error_code": event.last_error_code,
            "error": error_msg
        }

    async def run_tick(
        self,
        db: AsyncSession,
        batch_size: int = 10,
        lease_seconds: int = 30,
        timeout_budget_seconds: float = 25.0,
        trigger_type: str = "CRON"
    ) -> Dict[str, Any]:
        """
        Executes a bounded sweeper tick:
        1. Records worker run start in outbox_worker_runs.
        2. Claims up to batch_size eligible events atomically.
        3. Processes each event within the allocated execution time budget.
        4. Updates and persists run metrics and returns structured execution summary.
        """
        start_time = time.time()
        now = datetime.now(timezone.utc)

        # 1. Initialize run record
        run_record = OutboxWorkerRun(
            worker_id=self.worker_id,
            trigger_type=trigger_type,
            started_at=now,
            status="RUNNING"
        )
        db.add(run_record)
        await db.commit()

        claimed_count = 0
        processed_count = 0
        retry_count = 0
        dead_letter_count = 0
        aborted_by_timeout = False

        try:
            # 2. Claim batch
            events = await self.claim_batch(db, batch_size=batch_size, lease_seconds=lease_seconds)
            claimed_count = len(events)

            # 3. Process events respecting timeout budget
            for ev in events:
                elapsed = time.time() - start_time
                if elapsed > (timeout_budget_seconds - 3.0):
                    logger.warning(
                        f"[{self.worker_id}] Approaching timeout budget ({elapsed:.1f}s / {timeout_budget_seconds}s). "
                        f"Aborting batch early to guarantee clean response."
                    )
                    aborted_by_timeout = True
                    break

                res = await self.process_event(db, ev)
                if res.get("success"):
                    processed_count += 1
                elif res.get("is_dead_letter"):
                    dead_letter_count += 1
                else:
                    retry_count += 1

            # 4. Check remaining eligible events in queue
            stmt_rem = select(func.count(InstitutionalOutboxEvent.id)).where(
                and_(
                    InstitutionalOutboxEvent.status.in_(["PENDING", "RETRY_SCHEDULED"]),
                    InstitutionalOutboxEvent.available_at <= datetime.now(timezone.utc)
                )
            )
            res_rem = await db.execute(stmt_rem)
            remaining_count = res_rem.scalar_one()

            # 5. Finalize run record
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            run_record.completed_at = datetime.now(timezone.utc)
            run_record.duration_ms = duration_ms
            run_record.events_claimed = claimed_count
            run_record.events_processed = processed_count
            run_record.events_retry_scheduled = retry_count
            run_record.events_dead_lettered = dead_letter_count

            if aborted_by_timeout:
                run_record.status = "TIMEOUT_ABORTED"
                run_record.error_summary = f"Execution budget reached {duration_ms}ms"
            elif dead_letter_count > 0 or retry_count > 0:
                run_record.status = "PARTIAL_FAILURE"
            else:
                run_record.status = "SUCCESS"

            await db.commit()

            return {
                "status": "completed" if not aborted_by_timeout else "timeout_aborted",
                "worker_id": self.worker_id,
                "claimed": claimed_count,
                "processed": processed_count,
                "retry_scheduled": retry_count,
                "dead_lettered": dead_letter_count,
                "remaining_eligible": remaining_count > 0,
                "remaining_count": remaining_count,
                "duration_ms": duration_ms
            }

        except Exception as e:
            logger.error(f"[{self.worker_id}] Sweeper tick failed: {e}", exc_info=True)
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.duration_ms = int((time.time() - start_time) * 1000)
            run_record.status = "FAILED"
            run_record.error_summary = str(e)
            try:
                await db.commit()
            except Exception:
                await db.rollback()

            return {
                "status": "failed",
                "worker_id": self.worker_id,
                "claimed": claimed_count,
                "processed": processed_count,
                "retry_scheduled": retry_count,
                "dead_lettered": dead_letter_count,
                "remaining_eligible": False,
                "duration_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }

    @classmethod
    async def get_queue_metrics(cls, db: AsyncSession) -> Dict[str, Any]:
        """Returns real-time queue health, lease statistics, and outbox metrics."""
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
                InstitutionalOutboxEvent.status.in_(["PENDING", "RETRY_SCHEDULED"]),
                InstitutionalOutboxEvent.available_at <= now
            )
        )
        res_ready = await db.execute(stmt_ready)
        pending_ready = res_ready.scalar_one()

        # Active processing leases vs expired processing leases
        stmt_active_leases = select(func.count(InstitutionalOutboxEvent.id)).where(
            and_(
                InstitutionalOutboxEvent.status == "PROCESSING",
                InstitutionalOutboxEvent.lease_expires_at > now
            )
        )
        res_active_leases = await db.execute(stmt_active_leases)
        active_leases = res_active_leases.scalar_one()

        stmt_expired_leases = select(func.count(InstitutionalOutboxEvent.id)).where(
            and_(
                InstitutionalOutboxEvent.status == "PROCESSING",
                InstitutionalOutboxEvent.lease_expires_at.isnot(None),
                InstitutionalOutboxEvent.lease_expires_at <= now
            )
        )
        res_expired_leases = await db.execute(stmt_expired_leases)
        expired_leases = res_expired_leases.scalar_one()

        # Oldest pending event age in seconds
        stmt_oldest = (
            select(InstitutionalOutboxEvent.available_at)
            .where(
                and_(
                    InstitutionalOutboxEvent.status.in_(["PENDING", "RETRY_SCHEDULED"]),
                    InstitutionalOutboxEvent.available_at <= now
                )
            )
            .order_by(InstitutionalOutboxEvent.available_at.asc())
            .limit(1)
        )
        res_oldest = await db.execute(stmt_oldest)
        oldest_ts = res_oldest.scalar_one_or_none()
        oldest_pending_age_sec = int((now - oldest_ts).total_seconds()) if oldest_ts else 0

        # Last worker run
        stmt_last_run = (
            select(OutboxWorkerRun)
            .order_by(OutboxWorkerRun.started_at.desc())
            .limit(1)
        )
        res_run = await db.execute(stmt_last_run)
        last_run = res_run.scalar_one_or_none()

        last_run_info = None
        if last_run:
            last_run_info = {
                "worker_id": last_run.worker_id,
                "trigger_type": last_run.trigger_type,
                "status": last_run.status,
                "started_at": last_run.started_at.isoformat(),
                "duration_ms": last_run.duration_ms,
                "events_processed": last_run.events_processed
            }

        return {
            "queue_depth": (
                status_counts.get("PENDING", 0) +
                status_counts.get("RETRY_SCHEDULED", 0) +
                status_counts.get("PROCESSING", 0)
            ),
            "pending_ready": pending_ready,
            "retry_scheduled": status_counts.get("RETRY_SCHEDULED", 0),
            "processing": status_counts.get("PROCESSING", 0),
            "active_leases": active_leases,
            "expired_leases": expired_leases,
            "completed": status_counts.get("COMPLETED", 0),
            "failed": status_counts.get("FAILED", 0),
            "dead_letter": status_counts.get("DEAD_LETTER", 0),
            "oldest_pending_age_seconds": oldest_pending_age_sec,
            "last_worker_run": last_run_info,
            "timestamp": now.isoformat()
        }
