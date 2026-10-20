from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_admin, get_current_user_allow_unapproved
from domain.models.user import User
from domain.models.support import SupportTicket
from core.config import settings
from infrastructure.smtp.email_service import send_email
from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support"])


class ContactInquiryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    category: str = Field(..., max_length=60)
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=4000)
    reference_number: Optional[str] = Field(None, max_length=60)


async def _notify_admin_of_contact_inquiry(ticket_number: str, inquiry: ContactInquiryRequest):
    if not getattr(settings, "ADMIN_EMAIL", None):
        return
    admin_body = (
        f"New Public Support Inquiry Received:\n\n"
        f"Ticket Number: {ticket_number}\n"
        f"Name: {inquiry.name}\n"
        f"Email: {inquiry.email}\n"
        f"Category: {inquiry.category}\n"
        f"Reference ID: {inquiry.reference_number or 'N/A'}\n"
        f"Subject: {inquiry.subject}\n\n"
        f"Message:\n{inquiry.message}\n\n"
        f"Submitted at: {datetime.now(timezone.utc).isoformat()}"
    )
    try:
        await send_email(
            to_email=settings.ADMIN_EMAIL,
            subject=f"[Digital Rakshak Support] {ticket_number}: {inquiry.subject}",
            body=admin_body,
            reply_to=inquiry.email,
        )
    except Exception as exc:
        logger.warning(f"Failed to send admin contact notification email: {exc}")


@router.post("/contact")
async def submit_public_contact(
    inquiry: ContactInquiryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ticket_num = f"TKT-INQ-{uuid.uuid4().hex[:6].upper()}"
    initial_event = {
        "sender": "visitor",
        "name": inquiry.name,
        "email": inquiry.email,
        "category": inquiry.category,
        "reference_number": inquiry.reference_number,
        "message": inquiry.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    new_ticket = SupportTicket(
        ticket_number=ticket_num,
        user_id=None,
        subject=f"[{inquiry.category}] {inquiry.subject}",
        message=inquiry.message,
        status="open",
        history=[initial_event],
    )
    db.add(new_ticket)
    await db.commit()

    background_tasks.add_task(_notify_admin_of_contact_inquiry, ticket_num, inquiry)

    return {
        "success": True,
        "ticket_number": ticket_num,
        "message": "Inquiry received successfully. Our security and support teams will review your request promptly.",
    }


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
