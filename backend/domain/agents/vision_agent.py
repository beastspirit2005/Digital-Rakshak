import os
import json
from typing import Dict, Any, Optional
from google import genai
from core.config import settings

class VisionAgent:
    """
    Analyzes screenshots and image evidence to detect digital fraud.
    Uses Google Gemini Flash.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-1.5-flash"
        self.system_prompt = """You are an elite Cyber Threat Intelligence Vision AI.
Analyze the provided image (screenshot of a WhatsApp chat, bank transfer, email, etc.) for signs of a scam or digital fraud.
You MUST extract any text in the image.
You MUST output your analysis in raw JSON format matching this exact schema:
{
    "decision": "Scam or Safe with brief reason",
    "score": 0.5,
    "extracted_text": "Full text seen in the image",
    "phone_numbers": ["list of strings"],
    "urls": ["list of strings"],
    "upi_ids": ["list of strings"],
    "bank_accounts": ["list of strings"]
}
"""

    async def execute(self, payload: Dict[str, Any], case_id: str = "Unknown") -> Dict[str, Any]:
        image_path = payload.get("text", "")
        ai_mode = payload.get("ai_mode", "auto")
        analyze_type = payload.get("analyze_type", "scam") # 'scam' or 'counterfeit'
        
        if not os.path.exists(image_path):
            return {"error": "Image file not found"}
            
        # Determine offline mode
        from core.config import settings
        resolved_mode = ai_mode if ai_mode != "auto" else settings.DEFAULT_AI_MODE
        
        # OFFLINE MODE (Local PyTorch)
        if resolved_mode == "ollama" or settings.FORCE_LOCAL_INFERENCE:
            if analyze_type == "counterfeit":
                from infrastructure.ai.ml_client import RakshakVisionClient
                client = RakshakVisionClient()
                client.load_model()
                return client.detect_counterfeit(image_path)
            else:
                # Default OCR fallback for offline scam analysis
                from infrastructure.ai.ml_client import RakshakVisionClient
                client = RakshakVisionClient()
                client.load_model()
                extracted = client.extract_text(image_path)
                return {
                    "decision": "Manual Review Required (Offline OCR)",
                    "score": 0.5,
                    "extracted_text": extracted,
                    "evidence": ["Image analyzed via offline EasyOCR."]
                }
                
        # CLOUD MODE (Google Gemini Vision)
        try:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
                
            from google.genai import types
            
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp", "heic", "heif"] else "image/jpeg"
            
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            if analyze_type == "counterfeit":
                prompt = """You are an elite Currency Authentication AI.
Analyze the provided image of a currency note for signs of it being counterfeit (fake).
Check for watermarks, security threads, intaglio printing, and micro-lettering if visible.
You MUST output your analysis in raw JSON format matching this exact schema:
{
    "decision": "Counterfeit Currency Detected" or "Genuine Currency",
    "score": float between 0.0 and 1.0 (confidence),
    "threat_class": "Counterfeit Note",
    "evidence": ["List of anomalies detected, e.g., 'missing security thread', 'blurry micro-text'"]
}"""
            else:
                prompt = self.system_prompt
            
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            result = json.loads(response.text)
            result["models_used"] = ["gemini-1.5-flash-vision"]
            return result
        except Exception as e:
            print(f"Vision Analysis failed: {e}")
            return {"error": f"Vision analysis failed: {str(e)}"}
