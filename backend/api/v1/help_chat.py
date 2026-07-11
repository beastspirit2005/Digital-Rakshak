from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
from api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

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
    """Checks if any admin is currently online. (Simplified to always True for demo)"""
    return {"is_admin_online": True}

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
async def chat_endpoint(
    req: HelpChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Standard AI Chat endpoint (no streaming to keep Supabase Realtime simple).
    Takes a message, generates AI reply, and saves BOTH to Postgres so Supabase Realtime broadcasts them.
    """
    # 1. Save User Message
    user_msg = HelpMessage(
        session_id=req.session_id,
        role=HelpMessageRole.USER.value,
        content=req.message
    )
    db.add(user_msg)
    await db.commit()

    # 2. Fetch history for context
    result = await db.execute(
        select(HelpMessage)
        .where(HelpMessage.session_id == req.session_id)
        .order_by(HelpMessage.created_at.asc())
        .limit(10)
    )
    history = result.scalars().all()
    messages = [{"role": msg.role if msg.role in ["user", "assistant"] else "user", "content": msg.content} for msg in history]

    # 3. Generate AI Response
    system_prompt = {
        "role": "system",
        "content": "You are the Digital Rakshak AI Support Agent. Answer questions concisely and politely about reporting cyber crimes and using the platform. Do NOT mention you are an AI model like Gemini, Groq, or Ollama."
    }
    
    formatted_messages = [system_prompt] + messages

    # Check local vs cloud
    settings_result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = settings_result.scalar_one_or_none()
    force_local = settings.FORCE_LOCAL_INFERENCE
    if db_settings:
        force_local = db_settings.force_local_inference or db_settings.default_ai_mode == "ollama"

    full_reply = ""
    try:
        if force_local:
            client = ollama.AsyncClient()
            model_to_use = req.model if req.model else 'mistral'
            resp = await client.chat(model=model_to_use, messages=formatted_messages, stream=False)
            full_reply = resp.get('message', {}).get('content', "No response.")
        else:
            if not settings.GROQ_API_KEY:
                full_reply = "Groq API key is missing."
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": formatted_messages,
                            "temperature": 0.3,
                        },
                        timeout=30.0
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    full_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "No response.")
    except Exception as e:
        logger.error(f"AI failed: {e}")
        full_reply = "Sorry, our AI system is currently experiencing issues."

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
    db: AsyncSession = Depends(get_db)
):
    """Citizen requests human admin escalation."""
    sys_msg = HelpMessage(
        session_id=req.session_id,
        role=HelpMessageRole.SYSTEM.value,
        content="A citizen has requested live support. An admin has been notified and will join shortly."
    )
    db.add(sys_msg)
    await db.commit()
    return {"status": "escalated"}

@router.post("/admin-reply")
async def admin_reply_endpoint(
    req: AdminReplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin replies to a citizen."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can reply")
        
    admin_msg = HelpMessage(
        session_id=req.session_id,
        role=HelpMessageRole.ADMIN.value,
        content=req.message,
        user_id=user.id
    )
    db.add(admin_msg)
    await db.commit()
    return {"status": "success"}
