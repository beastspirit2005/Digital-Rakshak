from fastapi import APIRouter, Depends, UploadFile, File
import ollama
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/models")
async def list_models():
    """
    Returns a dynamic list of available AI models for the frontend dropdown.
    Includes Cloud (Gemini) models and fetches installed Local (Ollama) models.
    """
    models = []
    
    # 1. Add Cloud Models (Hardcoded Gemini)
    models.append({
        "id": "groq:llama-3.3-70b-versatile",
        "name": "Llama 3.3 (70B) Intelligence",
        "provider": "groq",
        "is_heavy": False,
        "is_recommended": True
    })
    models.append({
        "id": "groq:mixtral-8x7b-32768",
        "name": "Mixtral 8x7b (Groq)",
        "provider": "groq",
        "is_heavy": True,
        "is_recommended": False
    })
    
    # 2. Add Local Models (Fetch from Ollama)
    try:
        client = ollama.AsyncClient()
        response = await client.list()
        
        models_list = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
        
        for model in models_list:
            if isinstance(model, dict):
                model_name = model.get("model") or model.get("name", "")
            else:
                model_name = getattr(model, "model", "") or getattr(model, "name", "")
                
            if not model_name:
                continue
            
            # Determine if it's heavy based on parameter size naming conventions
            is_heavy = any(size in model_name for size in ["14b", "32b", "70b", "8x7b"])
            
            # Recommend Qwen2.5 7B based on system architecture 
            is_recommended = False
            if "qwen2.5" in model_name and "7b" in model_name:
                is_recommended = True
            elif "mistral" in model_name and not any(r["is_recommended"] for r in models if r["provider"] == "ollama"):
                # Fallback recommendation to mistral if qwen is missing
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
        # Provide fallback if Ollama is down
        models.append({
            "id": "ollama:mistral",
            "name": "Mistral (Local Offline)",
            "provider": "ollama",
            "is_heavy": False,
            "is_recommended": True
        })
        
    return {"models": models}

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts an audio file and transcribes it using Whisper or Gemini fallback.
    Returns just the raw text so the user can review/edit it before AI processing.
    """
    import os, uuid, shutil
    
    upload_dir = os.path.join(os.getcwd(), "uploads", "audio")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    safe_name = f"copilot_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(upload_dir, safe_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    from domain.agents.whisper_agent import WhisperAgent
    whisper = WhisperAgent()
    transcription = await whisper.execute(file_path)
    
    try:
        os.remove(file_path)
    except:
        pass
        
    return transcription

from pydantic import BaseModel

class TranscriptPayload(BaseModel):
    transcript: str

@router.post("/analyze-transcript")
async def analyze_transcript_draft(payload: TranscriptPayload):
    """
    Runs AI analysis on the verified transcript to extract entities and generate a case draft.
    """
    from core.config import settings
    from google import genai
    from google.genai import types
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
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, 
                response_mime_type="application/json"
            )
        )
        ai_result = json.loads(response.text)
        return {"draft": ai_result}
    except Exception as e:
        return {"error": f"AI analysis failed: {str(e)}"}
