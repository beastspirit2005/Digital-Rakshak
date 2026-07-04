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
        from domain.agents.router import AIRouter
        ai_router = AIRouter()
        # Create a single prompt combining system prompt, context, and user query
        full_prompt = f"{system_prompt}\n\n{context}\n\nINVESTIGATOR QUERY: {req.query}"
        
        # Use AIRouter to respect the global 'auto' setting or force_local
        ai_result = await ai_router.execute(prompt=full_prompt, context={}, ai_mode="auto")
        
        # AIRouter returns a dict. We just want the text response, so we grab the 'decision' or a default string.
        reply_text = ai_result.get("decision", "No response generated.") if isinstance(ai_result, dict) else str(ai_result)
        
        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error(f"Chat Co-Pilot failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")
