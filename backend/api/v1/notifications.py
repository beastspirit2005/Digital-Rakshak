"""
Notifications API
=================
REST endpoints for on-platform user notifications:
- List user notifications with filtering and pagination
- Query live unread badge count
- Mark individual or all notifications as read
- Dismiss notifications
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, desc

from infrastructure.db.session import get_db
from api.deps import get_current_user
from domain.models.user import User
from domain.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns the notification feed for the authenticated user, along with the unread count.
    """
    # Count unread notifications
    count_q = (
        select(func.count(Notification.id))
        .where(Notification.user_id == user.id, Notification.is_read == False)
    )
    unread_count = (await db.execute(count_q)).scalar() or 0

    # Query notifications
    query = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        query = query.where(Notification.is_read == False)

    res = await db.execute(query)
    items = res.scalars().all()

    return {
        "notifications": [item.to_dict() for item in items],
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lightweight polling endpoint to retrieve only the unread badge count.
    """
    count_q = (
        select(func.count(Notification.id))
        .where(Notification.user_id == user.id, Notification.is_read == False)
    )
    unread_count = (await db.execute(count_q)).scalar() or 0
    return {"unread_count": unread_count}


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Marks a specific notification as read.
    """
    try:
        n_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")

    res = await db.execute(
        select(Notification).where(Notification.id == n_uuid, Notification.user_id == user.id)
    )
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if not item.is_read:
        item.is_read = True
        item.read_at = datetime.now(timezone.utc)
        await db.commit()

    return {"status": "success", "id": str(item.id), "is_read": True}


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Marks all notifications for the authenticated user as read.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True, read_at=now)
    )
    await db.execute(stmt)
    await db.commit()

    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Dismisses and removes a notification.
    """
    try:
        n_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")

    stmt = delete(Notification).where(Notification.id == n_uuid, Notification.user_id == user.id)
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return {"status": "success", "message": "Notification dismissed"}
