from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging
import uuid
from infrastructure.db.session import get_db
from core.config import settings
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
from domain.models.case import Case
from api.deps import get_kb

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str
    
class ChatResponse(BaseModel):
    reply: str

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
    user: User = Depends(get_current_user)
):
    """
    Global AI Chatbot accessible by all roles with role-specific context injection and Prompt Injection protection.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    # 1. Prompt Injection Protection
    injection_patterns = [
        r"(?i)ignore all previous instructions",
        r"(?i)system prompt",
        r"(?i)forget everything",
        r"(?i)you are now",
        r"(?i)bypass",
        r"(?i)jailbreak",
        r"(?i)act as a",
        r"(?i)disregard",
        r"(?i)developer mode"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, req.query):
            logger.warning(f"Prompt injection attempt detected from user {user.id}")
            raise HTTPException(status_code=400, detail="Security Violation: Prompt Injection Attempt Detected.")

    role = user.role.lower() if user.role else ""
    user_id = str(user.id)
    
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
    from datetime import datetime
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    current_time_str = datetime.now(ist).strftime("%I:%M %p")
    
    # Query the RAG Knowledge Base
    kb = get_kb()
    laws = await kb.search_relevant_laws(db, req.query, top_k=2)
    patterns = await kb.search_fraud_patterns(db, req.query, top_k=1)
    
    rag_context = ""
    if laws:
        rag_context += "\nRELEVANT LAWS/GUIDELINES:\n"
        for law in laws:
            rag_context += f"- {law['title']} ({law['source']}): {law['content']}\n"
    if patterns:
        rag_context += "\nKNOWN FRAUD PATTERNS:\n"
        for p in patterns:
            rag_context += f"- {p['pattern']}: {p['description']}\n"
            
    if rag_context:
        context += f"\n\n{rag_context}"

    system_prompt = f"""
    You are the Digital Rakshak Global AI Assistant, an elite cybercrime and platform assistant.
    You are speaking to a user with the role of '{role}'. 
    Address them politely and assist them based on their authorization level. Do NOT greet them with their raw email or User ID. Keep your greeting natural (e.g., "Good morning!" or "Good evening!").
    The current time in India is {current_time_str}. Use this to formulate your greeting appropriately.
    
    Use the following CONTEXT to answer the user's query if relevant.
    CONTEXT:
    {context}
    
    Be helpful, concise, and professional.
    """
    
    full_prompt = f"{system_prompt}\n\nUSER QUERY: {req.query}"
    ai_mode = req.ai_mode.lower()

    try:
        if ai_mode == "groq" or ai_mode == "cloud":
            from infrastructure.ai.groq_client import GroqClient
            client = GroqClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="llama-3.1-8b-instant")
        else:
            from infrastructure.ai.ollama_client import OllamaClient
            client = OllamaClient()
            reply_text = await client.generate_text(prompt=full_prompt, model_name="mistral")
            
        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate chat response")

@router.post("/{case_id}/chat", response_model=ChatResponse)
async def case_copilot_chat(
    case_id: str, 
    req: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    AI Investigation Co-Pilot. Allows an investigator to ask questions about a specific case.
    """
    role = user.role
    if role not in ["admin", "police", "cyber_cell"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch Case
    try:
        parsed_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID format")
        
    result = await db.execute(select(Case).where(Case.id == parsed_uuid))
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
    
    # Query the RAG Knowledge Base
    kb = get_kb()
    
    # We combine the investigator's query and the case text for semantic search
    search_query = f"{req.query} {case.scam_text}"
    laws = await kb.search_relevant_laws(db, search_query, top_k=2)
    mistakes = await kb.search_past_mistakes(db, search_query, top_k=1)
    
    rag_context = ""
    if laws:
        rag_context += "\nRELEVANT LAWS/GUIDELINES:\n"
        for law in laws:
            rag_context += f"- {law['title']} ({law['source']}): {law['content']}\n"
            
    if mistakes:
        rag_context += "\nPAST AI MISTAKES TO AVOID (RLHF Memory):\n"
        for m in mistakes:
            rag_context += f"- Original: {m['original_scam']}\n  AI Guessed: {m['ai_got_wrong']}\n  Human Corrected: {m['human_correction']}\n"
            
    if rag_context:
        context += f"\n\n{rag_context}"

    system_prompt = """
    You are the Digital Rakshak Investigation Co-Pilot, an elite cybercrime assistant.
    The user is a police investigator asking about a specific case.
    I have provided you with the CASE FACT SHEET and relevant laws.
    Answer the investigator's query directly, accurately, and concisely based ONLY on the facts provided in the sheet and the laws.
    If the fact sheet does not contain the answer, say "I don't have that information in the case file."
    Do not hallucinate external details. Maintain a highly professional, law-enforcement tone.
    """

    try:
        # Respect global AI mode setting
        ai_mode = settings.DEFAULT_AI_MODE.lower()
        
        # Create a single prompt combining system prompt, context, and user query
        full_prompt = f"{system_prompt}\n\n{context}\n\nINVESTIGATOR QUERY: {req.query}"
        
        if ai_mode == "groq" or ai_mode == "cloud":
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



from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/support")
async def websocket_support_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # In a real system, we'd route this to an Admin if available.
            # Here we fallback to Groq/Ollama as requested if Admin is unavailable.
            await websocket.send_text(f"Automated AI Reply: I have received your message: '{data}'. An admin will join shortly.")
    except WebSocketDisconnect:
        logger.info("Client disconnected from support chat")
