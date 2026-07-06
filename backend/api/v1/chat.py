from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging
from infrastructure.db.session import get_db
from core.config import settings
from api.v1.users import get_current_user_token
from domain.models.case import Case
from infrastructure.ai.gemini_client import GeminiClient

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str
    
class ChatResponse(BaseModel):
    reply: str

@router.post("/{case_id}/chat", response_model=ChatResponse)
async def case_copilot_chat(
    case_id: str, 
    req: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    user_payload: dict = Depends(get_current_user_token)
):
    """
    AI Investigation Co-Pilot. Allows an investigator to ask questions about a specific case.
    """
    role = user_payload.get("role")
    if role not in ["admin", "police", "cyber_cell"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch Case
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build Context
    context = f"""
    CASE FACT SHEET
    ---------------
    Case Number: {case.case_number}
    Status: {case.status}
    Threat Level: {case.priority} (Score: {case.threat_confidence_score})
    Scam Type: {case.scam_type_code}
    
    RAW REPORT TEXT:
    {case.scam_text}
    
    AI INTELLIGENCE DATA:
    {case.ai_decision}
    """

    system_prompt = """
    You are the Digital Rakshak Investigation Co-Pilot, an elite cybercrime assistant.
    The user is a police investigator asking about a specific case.
    I have provided you with the CASE FACT SHEET.
    Answer the investigator's query directly, accurately, and concisely based ONLY on the facts provided in the sheet.
    If the fact sheet does not contain the answer, say "I don't have that information in the case file."
    Do not hallucinate external details. Maintain a highly professional, law-enforcement tone.
    """

    try:
        # Respect global AI mode setting
        ai_mode = settings.DEFAULT_AI_MODE.lower()
        
        # Create a single prompt combining system prompt, context, and user query
        full_prompt = f"{system_prompt}\n\n{context}\n\nINVESTIGATOR QUERY: {req.query}"
        
        if ai_mode == "cloud" or ai_mode == "gemini":
            from infrastructure.ai.gemini_client import GeminiClient
            client = GeminiClient()
            reply_text = await client.generate_text(prompt=full_prompt)
        elif ai_mode == "groq":
            from infrastructure.ai.groq_client import GroqClient
            client = GroqClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="llama-3.1-8b-instant")
        else:
            from infrastructure.ai.ollama_client import OllamaClient
            client = OllamaClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="mistral")
        
        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error(f"Chat Co-Pilot failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
from fastapi import Request
import re

class GlobalChatRequest(BaseModel):
    query: str
    ai_mode: str = "groq"
    case_id: str = None

@router.post("/global", response_model=ChatResponse)
@limiter.limit("10/minute")
async def global_chatbot(
    request: Request,
    req: GlobalChatRequest,
    db: AsyncSession = Depends(get_db),
    user_payload: dict = Depends(get_current_user_token)
):
    """
    Global AI Chatbot accessible by all roles with role-specific context injection and Prompt Injection protection.
    """
    # 1. Prompt Injection Protection
    injection_patterns = [
        r"(?i)ignore all previous instructions",
        r"(?i)system prompt",
        r"(?i)forget everything",
        r"(?i)you are now",
        r"(?i)bypass",
        r"(?i)jailbreak",
        r"(?i)act as a"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, req.query):
            raise HTTPException(status_code=400, detail="Security Violation: Prompt Injection Attempt Detected.")

    role = user_payload.get("role")
    user_id = user_payload.get("sub")
    
    # 2. Role-Based Context Retrieval
    context = "No additional context."
    
    if role == "citizen":
        # Citizen context: Summarize their recent cases
        result = await db.execute(select(Case).where(Case.submitted_by == user_id).order_by(Case.created_at.desc()).limit(5))
        cases = result.scalars().all()
        if cases:
            context = "USER'S RECENT CASES:\n"
            for c in cases:
                context += f"- Case {c.case_number}: Status {c.status}, Threat Level: {c.priority}\n"
        else:
            context = "User has no submitted cases yet."
            
    elif role == "police" or role == "cyber_cell":
        # Police context: Recent active cases
        result = await db.execute(select(Case).where(Case.status == 'submitted').order_by(Case.created_at.desc()).limit(5))
        cases = result.scalars().all()
        if cases:
            context = "RECENT UNASSIGNED CASES:\n"
            for c in cases:
                context += f"- Case {c.case_number} ({c.city}, {c.state}): Score {c.threat_confidence_score}\n"
                
    elif role == "admin":
        if req.case_id:
            result = await db.execute(select(Case).where(Case.case_number == req.case_id))
            case = result.scalar_one_or_none()
            if case:
                context = f"REQUESTED CASE {case.case_number}:\nStatus: {case.status}\nThreat: {case.priority}\nScam Text: {case.scam_text}\n"
            else:
                context = f"Requested case {req.case_id} not found."
        else:
            context = "Admin Global Access. You have full oversight of the Digital Rakshak platform."
            
    # 3. Construct System Prompt
    user_email = user_payload.get("email", "Unknown")
    
    system_prompt = f"""
    You are the Digital Rakshak Global AI Assistant.
    You are currently speaking to a user with the role of '{role}'.
    Their email address is '{user_email}' (User ID: {user_id}).
    Address them politely and assist them based on their authorization level.
    
    Use the following CONTEXT to answer the user's query if relevant.
    CONTEXT:
    {context}
    
    Be helpful, concise, and professional.
    """
    
    full_prompt = f"{system_prompt}\n\nUSER QUERY: {req.query}"
    ai_mode = req.ai_mode.lower()

    try:
        if ai_mode == "cloud" or ai_mode == "gemini":
            from infrastructure.ai.gemini_client import GeminiClient
            client = GeminiClient()
            reply_text = await client.generate_text(prompt=full_prompt)
        elif ai_mode == "groq":
            from infrastructure.ai.groq_client import GroqClient
            client = GroqClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="llama-3.1-8b-instant")
        else:
            from infrastructure.ai.ollama_client import OllamaClient
            client = OllamaClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="mistral")
            
        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error(f"Global Chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")
