from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_admin, get_current_user_allow_unapproved
from domain.models.user import User
from domain.models.support import SupportTicket
from datetime import datetime
import uuid

router = APIRouter(prefix="/support", tags=["Support"])

from typing import Optional

@router.post("/ticket")
async def create_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    chat_session_id: Optional[str] = Form(None),
    user: User = Depends(get_current_user_allow_unapproved),
    db: AsyncSession = Depends(get_db)
):
    new_ticket = SupportTicket(
        ticket_number=f"TKT-{uuid.uuid4().hex[:6].upper()}",
        user_id=user.id,
        subject=subject,
        message=message,
        chat_session_ref=chat_session_id,
        status="OPEN"
    )
    db.add(new_ticket)
    await db.commit()
    return {"message": "Ticket submitted successfully", "ticket_number": new_ticket.ticket_number}

@router.get("/tickets")
async def get_tickets(
    user: User = Depends(get_current_user_allow_unapproved),
    db: AsyncSession = Depends(get_db)
):
    if user.role == "admin":
        result = await db.execute(select(SupportTicket).order_by(desc(SupportTicket.created_at)))
    else:
        result = await db.execute(select(SupportTicket).where(SupportTicket.user_id == user.id).order_by(desc(SupportTicket.created_at)))
    
    tickets = result.scalars().all()
    return {"tickets": tickets}

@router.post("/ticket/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: str,
    admin_reply: str = Form(...),
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalars().first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    # Initialize history if None
    if ticket.history is None:
        ticket.history = []
        
    # Append to history instead of overwriting
    # We must assign a new list to trigger SQLAlchemy's JSON mutation detection
    new_history = list(ticket.history)
    new_history.append({
        "sender": "admin", 
        "message": admin_reply,
        "timestamp": datetime.now().isoformat()
    })
    ticket.history = new_history
    
    ticket.status = "ANSWERED"
    await db.commit()
    
    return {"message": "Reply saved successfully"}
