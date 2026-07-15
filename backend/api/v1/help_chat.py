from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
import httpx
import ollama
import asyncio
from core.config import settings
from infrastructure.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.models.settings import PlatformSettings
from domain.models.help_message import HelpMessage, HelpMessageRole
from domain.models.support import SupportTicket, TicketStatus
from domain.models.user import User
from api.deps import get_current_user, get_current_user_allow_unapproved, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class HelpChatRequest(BaseModel):
    session_id: str
    message: str
    role: str = "citizen"
    model: Optional[str] = None

class EscalateRequest(BaseModel):
    session_id: str
    client_id: str

class AdminReplyRequest(BaseModel):
    session_id: str
    message: str

@router.get("/admin-status")
async def get_admin_status(db: AsyncSession = Depends(get_db)):
    """Check if admin has active escalated sessions to respond to."""
    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.role == HelpMessageRole.SYSTEM.value)
    )
    escalations = result.scalars().all()
    
    admin_available = False
    for escalation in escalations:
        has_admin_reply = await db.execute(
            select(HelpMessage)
            .where(
                (HelpMessage.session_id == escalation.session_id) &
                (HelpMessage.role == HelpMessageRole.ADMIN.value)
            )
            .limit(1)
        )
        if has_admin_reply.scalars().first():
            admin_available = True
            break
            
    return {
        "is_admin_online": admin_available,
        "pending_escalations": len(escalations)
    }

@router.get("/chat-settings")
async def get_chat_settings(db: AsyncSession = Depends(get_db)):
    """Returns the chat settings to determine if local mode is forced."""
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = result.scalar_one_or_none()
    
    force_local = settings.FORCE_LOCAL_INFERENCE
    if db_settings:
        force_local = db_settings.force_local_inference or db_settings.default_ai_mode == "ollama"
        
    return {"force_local_inference": force_local}

@router.post("/chat")
@limiter.limit("20/minute")
async def chat_endpoint(
    request: Request,
    req: HelpChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Standard AI Chat endpoint (no streaming to keep Supabase Realtime simple).
    Takes a message, generates AI reply, and saves BOTH to Postgres so Supabase Realtime broadcasts them.
    """
    # Validate input
    if not req.session_id or len(req.session_id.strip()) < 8:
        raise HTTPException(status_code=400, detail="Invalid session ID (min 8 chars)")
    
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    if len(req.message) > 5000:
        raise HTTPException(status_code=400, detail="Message too long (max 5000 characters)")

    # 1. Save User Message
    user_msg = HelpMessage(
        session_id=req.session_id,
        user_id=user.id if user else None,
        role=HelpMessageRole.USER.value,
        content=req.message
    )
    db.add(user_msg)
    await db.commit()

    # 2. Fetch history for context (only user/assistant)
    # Fetch the LATEST 10 messages
    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.session_id == req.session_id)
        .where(HelpMessage.role.in_([HelpMessageRole.USER.value, HelpMessageRole.ASSISTANT.value]))
        .order_by(HelpMessage.created_at.desc())
        .limit(10)
    )
    history = result.scalars().all()
    # Reverse to make it chronological
    history.reverse()
    
    messages = [
        {"role": msg.role, "content": msg.content} 
        for msg in history
    ]

    # 3. Generate AI Response
    system_prompt = {
        "role": "system",
        "content": "You are the Digital Rakshak AI Support Agent. Answer questions concisely and politely about reporting cyber crimes and using the platform. Do NOT mention you are an AI model like Groq or Ollama."
    }
    
    formatted_messages = [system_prompt] + messages

    # Validate messages before sending
    if not formatted_messages:
        full_reply = "Unable to process your request. Please try again."
        logger.warning(f"No valid messages for session {req.session_id}")
    elif not any(msg.get("content") and msg.get("content").strip() for msg in formatted_messages):
        full_reply = "No message content to process. Please try again."
        logger.warning(f"Empty message content for session {req.session_id}")
    else:
        full_reply = ""
        try:
            # Check local vs cloud
            settings_result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
            db_settings = settings_result.scalar_one_or_none()
            force_local = settings.FORCE_LOCAL_INFERENCE
            if db_settings:
                force_local = db_settings.force_local_inference or db_settings.default_ai_mode == "ollama"

            if force_local:
                try:
                    client = ollama.AsyncClient()
                    model_to_use = req.model if req.model else 'mistral'
                    logger.info(f"Using local Ollama model: {model_to_use}")
                    resp = await client.chat(model=model_to_use, messages=formatted_messages, stream=False)
                    full_reply = resp.get('message', {}).get('content', "").strip()
                    
                    if not full_reply:
                        logger.warning(f"Ollama returned empty response for model {model_to_use}")
                        full_reply = "Sorry, I couldn't generate a response. Please try again."
                except Exception as ollama_err:
                    logger.error(f"Ollama error: {ollama_err}")
                    full_reply = ""  # Clear so cloud fallback triggers below
                    force_local = False  # Fallback to Groq
            
            # Cloud fallback
            if not force_local and not full_reply:
                if not settings.GROQ_API_KEY:
                    logger.error("Groq API key is missing")
                    full_reply = "Groq API key is not configured."
                else:
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            logger.info("Calling Groq API")
                            resp = await client.post(
                                "https://api.groq.com/openai/v1/chat/completions",
                                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                                json={
                                    "model": "llama-3.3-70b-versatile",
                                    "messages": formatted_messages,
                                    "temperature": 0.3,
                                },
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            full_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                            
                            if not full_reply:
                                logger.warning("Groq API returned empty content")
                                full_reply = "Sorry, I couldn't generate a response. Please try again."
                    except httpx.TimeoutException:
                        logger.error("Groq API timeout")
                        full_reply = "Request timed out. Please try again."
                    except httpx.HTTPStatusError as http_err:
                        logger.error(f"Groq API HTTP error: {http_err.response.status_code} - {http_err}")
                        full_reply = f"AI service error: {http_err.response.status_code}. Please try again."
                    except Exception as groq_err:
                        logger.error(f"Groq API error: {groq_err}")
                        full_reply = "Cloud service unavailable. Please try again."
                        
        except Exception as e:
            logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
            full_reply = "Sorry, our AI system is currently experiencing issues."

    # Ensure full_reply is not empty
    if not full_reply or not full_reply.strip():
        full_reply = "Sorry, I couldn't generate a response. Please try again."
        logger.warning(f"Empty response detected, using fallback for session {req.session_id}")

    # 4. Save AI Reply
    ai_msg = HelpMessage(
        session_id=req.session_id,
        role=HelpMessageRole.ASSISTANT.value,
        content=full_reply
    )
    db.add(ai_msg)
    await db.commit()
    
    return {"status": "success", "reply": full_reply}

@router.post("/escalate")
async def escalate_endpoint(
    req: EscalateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_allow_unapproved)
):
    """Citizen requests human admin escalation."""
    from uuid import UUID
    
    try:
        client_uuid = UUID(user.id) if isinstance(user.id, str) else user.id
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    sys_msg = HelpMessage(
        session_id=req.session_id,
        user_id=client_uuid,
        role=HelpMessageRole.SYSTEM.value,
        content="A citizen has requested live support. An admin has been notified and will join shortly."
    )
    db.add(sys_msg)
    
    # Auto-draft a Support Ticket
    # 1. Fetch chat history to append as context
    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.session_id == req.session_id)
        .order_by(HelpMessage.created_at.asc())
    )
    history_msgs = result.scalars().all()
    
    ticket_history = []
    for m in history_msgs:
        ticket_history.append({
            "sender": m.role,
            "message": m.content,
            "timestamp": m.created_at.isoformat() if m.created_at else None
        })
        
    import uuid
    new_ticket = SupportTicket(
        ticket_number=f"TKT-{uuid.uuid4().hex[:6].upper()}",
        user_id=client_uuid,
        subject=f"Live Chat Escalation - {str(client_uuid)[:8]}",
        message="This ticket was automatically generated from a live chat escalation.",
        chat_session_ref=req.session_id,
        status="LIVE_CHAT",
        history=ticket_history
    )
    db.add(new_ticket)
    
    await db.commit()
    return {"status": "escalated", "ticket_number": new_ticket.ticket_number}

@router.get("/messages/{session_id}")
@limiter.limit("60/minute")
async def get_citizen_messages(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Returns all messages for a citizen's help chat session."""
    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.session_id == session_id)
        .order_by(HelpMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return {"messages": [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        } for msg in messages
    ]}

@router.get("/admin/sessions")
async def get_escalated_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns all chat sessions that have been escalated to humans or are active."""
    allowed_roles = ["admin", "police", "cyber_cell", "bank_employee", "banker"]
    print(f"DEBUG: user.role is {repr(user.role)}")
    if user.role not in allowed_roles:
        print(f"DEBUG: raising 403 because {repr(user.role)} not in {allowed_roles}")
        raise HTTPException(status_code=403, detail="Support agents only")

    # Find distinct user_ids and session_ids that have escalation system messages
    result = await db.execute(
        select(HelpMessage.user_id, HelpMessage.session_id)
        .where(HelpMessage.role == HelpMessageRole.SYSTEM.value)
        .distinct()
    )
    escalations = result.all()
    
    # For each escalation, get the user info
    sessions = []
    # Deduplicate by session_id in python just in case of multiple user_ids
    seen_sessions = set()
    
    for user_id, session_id in escalations:
        if session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)
        
        citizen_data = {
            "session_id": session_id,
            "citizen_name": "Unknown Citizen",
            "user_id": str(user_id) if user_id else None,
            "email": "N/A",
            "ticket_count": 0
        }
        
        if user_id:
            citizen = await db.get(User, user_id)
            if citizen:
                citizen_data["citizen_name"] = citizen.full_name
                citizen_data["email"] = citizen.email
                
        sessions.append(citizen_data)
    
    return {"sessions": sessions}

@router.get("/admin/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns all messages for a given help chat session."""
    allowed_roles = ["admin", "police", "cyber_cell", "bank_employee", "banker"]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Support agents only")

    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.session_id == session_id)
        .order_by(HelpMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return {"messages": [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        } for msg in messages
    ]}

@router.post("/admin-reply")
async def admin_reply_endpoint(
    req: AdminReplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin replies to a citizen."""
    allowed_roles = ["admin", "police", "cyber_cell", "bank_employee", "banker"]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only support agents can reply")
        
    admin_msg = HelpMessage(
        session_id=req.session_id,
        role=HelpMessageRole.ADMIN.value,
        content=req.message,
        user_id=user.id
    )
    db.add(admin_msg)
    await db.commit()
    return {"status": "success"}

