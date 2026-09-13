from fastapi import APIRouter, Depends, UploadFile, File
from api.deps import get_current_user, get_current_admin, get_current_user_allow_unapproved
from domain.models.user import User
from core.config import settings
import ollama
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/models")
async def list_models(user: User = Depends(get_current_user_allow_unapproved)):
    """
    Returns a dynamic list of available AI models for the frontend dropdown.
    Includes Cloud (Groq) models and fetches installed Local (Ollama) models.
    """
    models = []
    
    # 1. Add Cloud Models (Hardcoded Groq)
    models.append({
        "id": "groq:openai/gpt-oss-20b",
        "name": "GPT-OSS 20B (Groq)",
        "provider": "groq",
        "is_heavy": False,
        "is_recommended": True
    })
    models.append({
        "id": "groq:llama-3.2-3b-preview",
        "name": "Llama 3.2 (3B) Fast",
        "provider": "groq",
        "is_heavy": False,
        "is_recommended": False
    })
    
    # 2. Add Local Models (Fetch from Ollama)
    try:
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        response = await client.list()
        
        models_list = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
        
        for model in models_list:
            if isinstance(model, dict):
                model_name = model.get("model") or model.get("name", "")
            else:
                model_name = getattr(model, "model", "") or getattr(model, "name", "")
                
            if not model_name:
                continue
            
            # Filter out legacy models that may linger
            if any(old in model_name.lower() for old in ["mistral", "qwen2.5:7b"]):
                continue

            # Determine if it's heavy based on parameter size naming conventions
            is_heavy = any(size in model_name for size in ["14b", "27b", "32b", "70b", "8x7b"])
            
            # Recommend llama3:8b as the fast, default local offline model
            is_recommended = False
            if "llama3" in model_name and "8b" in model_name:
                is_recommended = True
            elif "qwen3.8" in model_name and not any(r["is_recommended"] for r in models if r["provider"] == "ollama"):
                is_recommended = True
                
            models.append({
                "id": f"ollama:{model_name}",
                "name": model_name,
                "provider": "ollama",
                "is_heavy": is_heavy,
                "is_recommended": is_recommended
            })
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama models: {e}. Is Ollama running?")
        # Provide fallback if Ollama is down with current device models
        models.append({
            "id": "ollama:llama3:8b",
            "name": "Llama 3 (8B Local Offline)",
            "provider": "ollama",
            "is_heavy": False,
            "is_recommended": True
        })
        models.append({
            "id": "ollama:qwen3.8:27b",
            "name": "Qwen 3.8 (27B Local Offline)",
            "provider": "ollama",
            "is_heavy": True,
            "is_recommended": False
        })
        models.append({
            "id": "ollama:gemma4:12b",
            "name": "Gemma 4 (12B Local Offline)",
            "provider": "ollama",
            "is_heavy": False,
            "is_recommended": False
        })
        
    return {"models": models}

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """
    Accepts an audio file and transcribes it using Whisper or Groq fallback.
    Returns just the raw text so the user can review/edit it before AI processing.
    """
    import os, uuid, shutil
    
    # Security: File extension and MIME type validation
    allowed_extensions = {".webm", ".mp3", ".wav", ".ogg", ".m4a"}
    file_ext = os.path.splitext(file.filename or "audio.webm")[1].lower()
    
    if file_ext not in allowed_extensions:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are allowed.")
        
    # Security: Size limit (max 10MB)
    if file.size is not None and file.size > 10 * 1024 * 1024:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
    import tempfile
    upload_dir = tempfile.gettempdir()
    
    safe_name = f"copilot_{str(user.id)}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(upload_dir, safe_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        from domain.agents.whisper_agent import WhisperAgent
        whisper = WhisperAgent()
        transcription = await whisper.execute({"text": file_path})
        return transcription
    finally:
        for _ in range(3):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                break
            except PermissionError:
                await asyncio.sleep(0.1)
            except Exception:
                break

from pydantic import BaseModel

class TranscriptPayload(BaseModel):
    transcript: str

@router.post("/analyze-transcript")
async def analyze_transcript_draft(payload: TranscriptPayload, user: User = Depends(get_current_user)):
    """
    Runs AI analysis on the verified transcript to extract entities and generate a case draft.
    """
    from infrastructure.ai.groq_client import GroqClient
    import json
    
    analysis_prompt = f"""Analyze this transcribed scam report from a victim/investigator and extract structured data.

Transcript: {payload.transcript}

Respond ONLY with a JSON object:
{{
    "scam_type": "Digital Arrest / UPI Fraud / Phishing / etc.",
    "confidence": 0.95,
    "entities": {{
        "phone_numbers": ["+91..."],
        "bank_accounts": ["SBI / HDFC details"],
        "upi_ids": ["xyz@bank"],
        "urls": ["http://..."],
        "impersonation": "Police / CBI / FedEx / etc."
    }},
    "recommended_actions": ["Block phone", "Alert bank", "File FIR under Section X"]
}}"""
    
    try:
        client = GroqClient()
        response_text = await client.generate_text(analysis_prompt, model_name="openai/gpt-oss-120b")
        
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            ai_result = json.loads(json_match.group(0))
        else:
            ai_result = json.loads(response_text)
            
        return {"draft": ai_result}
    except Exception as e:
        return {"error": f"AI analysis failed: {str(e)}"}
