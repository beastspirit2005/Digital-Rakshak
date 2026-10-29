"""
Notification Service
====================
Centralized on-platform event dispatcher that generates and routes notifications
to appropriate personas (Admin, Investigation Officer, Bank Nodal Officer, Citizen).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from domain.models.notification import Notification
from domain.models.user import User
from domain.models.case import Case

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: Any,
        title: str,
        message: str,
        type: str = "system_notice",
        priority: str = "normal",
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Notification]:
        """
        Creates and persists an on-platform notification record for a user.
        Accepts UUID or string UUID.
        """
        try:
            target_uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
            notif = Notification(
                id=uuid.uuid4(),
                user_id=target_uid,
                title=title,
                message=message,
                type=type,
                priority=priority,
                link=link,
                metadata_json=metadata or {},
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(notif)
            logger.info(f"Notification queued for user {target_uid}: [{type}] {title}")
            return notif
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            return None

    @staticmethod
    async def notify_case_message(
        db: AsyncSession,
        case: Case,
        sender: User,
        content: str,
    ) -> List[Notification]:
        """
        Pings the appropriate counterpart when a direct case chat message is posted:
        - If sender is Citizen: Pings the assigned officer. If unassigned, pings jurisdictional duty desk officers.
        - If sender is Officer/Admin: Pings the citizen complainant.
        """
        notifications = []
        is_citizen = sender.role == "citizen"
        snippet = content[:80] + ("..." if len(content) > 80 else "")

        if is_citizen:
            # Citizen sent a message -> Ping assigned officer
            assigned_officer_id = getattr(case, "assigned_to", None)

            if assigned_officer_id:
                notif = await NotificationService.create_notification(
                    db=db,
                    user_id=assigned_officer_id,
                    title=f"New Message on Case #{case.case_number}",
                    message=f"{sender.full_name or 'Citizen Complainant'} sent a direct message: \"{snippet}\"",
                    type="chat_message",
                    priority="high",
                    link=f"/workbench/reports",
                    metadata={
                        "case_id": str(case.id),
                        "case_number": case.case_number,
                        "sender_id": str(sender.id),
                        "sender_name": sender.full_name or "Complainant",
                    },
                )
                if notif:
                    notifications.append(notif)
            else:
                # Case is unassigned: Alert active Cyber Cell officers in the district/state so case isn't abandoned
                state_query = select(User).where(
                    User.role.in_(["police", "cyber_cell"]),
                    User.is_active == True,
                    User.is_approved == True,
                )
                if case.state:
                    state_query = state_query.where(User.state.ilike(f"%{case.state.strip()}%"))

                res = await db.execute(state_query.limit(5))
                officers = res.scalars().all()

                for off in officers:
                    notif = await NotificationService.create_notification(
                        db=db,
                        user_id=off.id,
                        title=f"Direct Chat Request on Unassigned Case #{case.case_number}",
                        message=f"Complainant {sender.full_name or 'Victim'} requested assistance: \"{snippet}\"",
                        type="chat_message",
                        priority="urgent",
                        link="/workbench",
                        metadata={
                            "case_id": str(case.id),
                            "case_number": case.case_number,
                            "unassigned": True,
                        },
                    )
                    if notif:
                        notifications.append(notif)

        else:
            # Officer or Admin replied -> Ping the citizen victim
            victim_id = getattr(case, "submitted_by", None)
            if victim_id and victim_id != sender.id:
                officer_title = f"Officer {sender.full_name}" if sender.full_name else "Assigned Investigator"
                notif = await NotificationService.create_notification(
                    db=db,
                    user_id=victim_id,
                    title=f"Officer Response on Case #{case.case_number}",
                    message=f"{officer_title} replied to your case: \"{snippet}\"",
                    type="chat_message",
                    priority="high",
                    link="/citizen",
                    metadata={
                        "case_id": str(case.id),
                        "case_number": case.case_number,
                        "sender_id": str(sender.id),
                        "sender_name": sender.full_name or "Investigator",
                    },
                )
                if notif:
                    notifications.append(notif)

        return notifications

    @staticmethod
    async def notify_admins(
        db: AsyncSession,
        title: str,
        message: str,
        type: str = "system_notice",
        priority: str = "normal",
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Notification]:
        """
        Broadcasts an operational alert to all platform administrators (KYC reviews, misconduct allegations).
        """
        res = await db.execute(select(User).where(User.role == "admin", User.is_active == True))
        admins = res.scalars().all()
        notifications = []
        for admin in admins:
            n = await NotificationService.create_notification(
                db=db,
                user_id=admin.id,
                title=title,
                message=message,
                type=type,
                priority=priority,
                link=link,
                metadata=metadata,
            )
            if n:
                notifications.append(n)
        return notifications

    @staticmethod
    async def notify_nodal_officers(
        db: AsyncSession,
        title: str,
        message: str,
        link: str = "/banker",
        priority: str = "high",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Notification]:
        """
        Broadcasts urgent lien and takedown requests to bank nodal officers.
        """
        res = await db.execute(
            select(User).where(
                User.role.in_(["banker", "bank_employee"]),
                User.is_active == True,
                User.is_approved == True,
            ).limit(10)
        )
        nodals = res.scalars().all()
        notifications = []
        for nodal in nodals:
            n = await NotificationService.create_notification(
                db=db,
                user_id=nodal.id,
                title=title,
                message=message,
                type="takedown_alert",
                priority=priority,
                link=link,
                metadata=metadata,
            )
            if n:
                notifications.append(n)
        return notifications

    @staticmethod
    async def notify_citizen_case_update(
        db: AsyncSession,
        case: Case,
        new_status: str,
    ) -> Optional[Notification]:
        """
        Informs the citizen complainant when their case progress milestone transitions.
        """
        victim_id = getattr(case, "submitted_by", None)
        if not victim_id:
            return None

        status_formatted = new_status.replace("_", " ").title()
        return await NotificationService.create_notification(
            db=db,
            user_id=victim_id,
            title=f"Case Milestone Update: #{case.case_number}",
            message=f"Your cyber fraud complaint status has updated to: {status_formatted}",
            type="case_status",
            priority="normal",
            link="/citizen",
            metadata={"case_id": str(case.id), "case_number": case.case_number, "status": new_status},
        )
