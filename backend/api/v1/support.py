from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
from domain.models.support import SupportTicket
from datetime import datetime
import uuid

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/ticket")
async def create_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_ticket = SupportTicket(
        ticket_number=f"TKT-{uuid.uuid4().hex[:6].upper()}",
        user_id=str(user.id),
        subject=subject,
        message=message,
        status="OPEN"
    )
    db.add(new_ticket)
    await db.commit()
    return {"message": "Ticket submitted successfully", "ticket_number": new_ticket.ticket_number}

@router.get("/tickets")
async def get_tickets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role == "admin":
        result = await db.execute(select(SupportTicket).order_by(desc(SupportTicket.created_at)))
    else:
        result = await db.execute(select(SupportTicket).where(SupportTicket.user_id == str(user.id)).order_by(desc(SupportTicket.created_at)))
    
    tickets = result.scalars().all()
    return {"tickets": tickets}
