from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional

logger = logging.getLogger("runtime.sla_monitor_daemon")

SLA_LIMITS_HOURS = {
    "critical": 24,
    "high": 48,
    "standard": 72,
    "medium": 72,
    "low": 96,
}

COOLDOWN_HOURS = 12  # Minimum hours between automated SLA reminder dispatches per case

class SLAMonitorDaemon:
    """
    Background worker that proactively evaluates all active cases against their
    priority-based investigation SLAs. Dispatches in-app notifications to Admins
    and assigned Investigators when cases breach their SLA limits.
    """

    def __init__(self) -> None:
        self.last_run_at: Optional[datetime] = None
        self.last_overdue_count: int = 0
        self._daemon_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    async def check_cases_sla(self) -> int:
        """
        Scans all cases in 'assigned' or 'investigating' status.
        Dispatches alerts for SLA breaches past their cooldown window.
        """
        from infrastructure.db.session import AsyncSessionLocal
        from domain.models.case import Case, CaseStatus
        from domain.models.user import User
        from domain.services.notification_service import NotificationService
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified

        now_utc = datetime.now(timezone.utc)
        self.last_run_at = now_utc
        notified_count = 0

        try:
            async with AsyncSessionLocal() as session:
                query = select(Case).where(
                    Case.status.in_([
                        CaseStatus.investigating.value,
                        "investigating",
                        CaseStatus.assigned.value,
                        "assigned"
                    ])
                )
                res = await session.execute(query)
                cases = res.scalars().all()

                if not cases:
                    self.last_overdue_count = 0
                    return 0

                # Load officers for assigned cases
                assignee_ids = {c.assigned_to for c in cases if c.assigned_to}
                officers_map = {}
                if assignee_ids:
                    u_res = await session.execute(select(User).where(User.id.in_(assignee_ids)))
                    for u in u_res.scalars().all():
                        officers_map[u.id] = u

                for c in cases:
                    dna = dict(c.attack_dna or {})
                    claimed_at_str = dna.get("claimed_at")

                    ref_time = None
                    if claimed_at_str:
                        try:
                            ref_time = datetime.fromisoformat(claimed_at_str.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    if not ref_time and c.updated_at:
                        ref_time = c.updated_at.replace(tzinfo=timezone.utc) if c.updated_at.tzinfo is None else c.updated_at
                    if not ref_time and c.created_at:
                        ref_time = c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at

                    if not ref_time:
                        continue

                    elapsed_hours = (now_utc - ref_time).total_seconds() / 3600
                    priority_key = (getattr(c, "urgency_level", "") or c.priority or "standard").lower()
                    limit_hours = SLA_LIMITS_HOURS.get(priority_key, 72)

                    if elapsed_hours > limit_hours:
                        hours_overdue = round(elapsed_hours - limit_hours, 1)

                        # Check cooldown against last reminder dispatched
                        last_reminder_str = dna.get("last_sla_reminder_at")
                        can_notify = True
                        if last_reminder_str:
                            try:
                                last_rem_dt = datetime.fromisoformat(last_reminder_str.replace("Z", "+00:00"))
                                if (now_utc - last_rem_dt).total_seconds() / 3600 < COOLDOWN_HOURS:
                                    can_notify = False
                            except Exception:
                                pass

                        if not can_notify:
                            continue

                        now_iso = now_utc.isoformat()
                        officer = officers_map.get(c.assigned_to)
                        officer_name = officer.full_name if officer else "Assigned Officer"

                        # 1. Dispatch in-app alert to All Admins
                        try:
                            await NotificationService.notify_admins(
                                db=session,
                                title=f"⏰ SLA Overdue Alert: Case #{c.case_number}",
                                message=f"Case #{c.case_number} ({priority_key.upper()}) is overdue by {hours_overdue}h (Allowed {limit_hours}h). Lead Officer: {officer_name}.",
                                type="case_assigned",
                                priority="urgent",
                                link=f"/admin/tracker?case={c.case_number}",
                                metadata={
                                    "case_id": str(c.id),
                                    "case_number": c.case_number,
                                    "hours_overdue": hours_overdue,
                                    "limit_hours": limit_hours,
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to notify admins of SLA overdue for case {c.case_number}: {e}")

                        # 2. Dispatch reminder to assigned officer (if assigned)
                        if c.assigned_to:
                            try:
                                await NotificationService.create_notification(
                                    db=session,
                                    user_id=c.assigned_to,
                                    title=f"Case SLA Overdue Notice: #{c.case_number}",
                                    message=f"Investigation for Case #{c.case_number} has exceeded its {limit_hours}h SLA limit (+{hours_overdue}h). Please submit an evidentiary progress update.",
                                    type="case_assigned",
                                    priority="high",
                                    link=f"/workbench/reports?case={c.case_number}&action=nudge",
                                    metadata={
                                        "case_id": str(c.id),
                                        "case_number": c.case_number,
                                        "hours_overdue": hours_overdue,
                                        "action": "nudge",
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Failed to notify investigator {c.assigned_to} of SLA overdue: {e}")

                        # 3. Append to timeline & update attack_dna
                        events = list(c.timeline_events or [])
                        events.append({
                            "action": "Automated SLA Overdue Alert",
                            "author": "System SLA Monitor",
                            "method": "sla_daemon",
                            "remark": f"Automated monitor flagged investigation delay of +{hours_overdue}h beyond {limit_hours}h SLA.",
                            "timestamp": now_iso
                        })
                        c.timeline_events = events
                        flag_modified(c, "timeline_events")

                        dna["last_sla_reminder_at"] = now_iso
                        dna["sla_breached"] = True
                        dna["hours_overdue"] = hours_overdue
                        if c.assigned_to:
                            dna["nudge_pending"] = True
                            dna["last_nudged_at"] = now_iso
                        c.attack_dna = dna
                        flag_modified(c, "attack_dna")

                        notified_count += 1

                if notified_count > 0:
                    await session.commit()
                    logger.info(f"[SLA Monitor] Evaluated {len(cases)} cases. Dispatched alerts for {notified_count} overdue cases.")

                self.last_overdue_count = notified_count
                return notified_count

        except Exception as exc:
            logger.error(f"[SLA Monitor] Error running SLA check: {exc}", exc_info=True)
            return 0

    async def start_daemon(self, interval_seconds: int = 3600) -> None:
        """
        Starts the continuous background loop. Runs initially after 60s warmup,
        then repeats every `interval_seconds` (default: 1 hour).
        """
        if self._is_running:
            logger.info("[SLA Monitor] Daemon is already running.")
            return

        self._is_running = True
        logger.info(f"[SLA Monitor] Starting automated SLA background monitor. Check interval: {interval_seconds}s.")

        # Brief warmup delay after server boots
        await asyncio.sleep(45)

        while self._is_running:
            try:
                await self.check_cases_sla()
            except asyncio.CancelledError:
                logger.info("[SLA Monitor] Daemon task cancelled.")
                break
            except Exception as e:
                logger.error(f"[SLA Monitor] Unexpected loop error: {e}")

            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break

    def stop_daemon(self) -> None:
        self._is_running = False
        if self._daemon_task and not self._daemon_task.done():
            self._daemon_task.cancel()


sla_monitor_daemon = SLAMonitorDaemon()
