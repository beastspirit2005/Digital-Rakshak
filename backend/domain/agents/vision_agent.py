import os
import json
from typing import Dict, Any, Optional
from core.config import settings

class VisionAgent:
    """
    Analyzes screenshots and image evidence to detect digital fraud.
    Uses Groq Llama 3.2 Vision.
    """
    
    def __init__(self):
        self.model = "llama-3.2-90b-vision-preview"
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
                
        # CLOUD MODE (Groq Vision)
        try:
            import base64
            import httpx
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
                
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp"] else "image/jpeg"
            
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
            
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                        ]
                    }
                ],
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload_data, timeout=60.0)
                if response.status_code != 200:
                    print(f"Groq API Error: {response.text}")
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                import re
                print(f"Raw Groq Response: {content}")
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                
                try:
                    result_raw = json.loads(content)
                    # Normalize keys to lowercase to avoid frontend mapping issues
                    result = {k.lower(): v for k, v in result_raw.items()}
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON from Groq: {content}")
                    result = {
                        "decision": "Error parsing AI response",
                        "score": 0.0,
                        "threat_class": "Unknown",
                        "evidence": [f"Raw text: {content}"]
                    }
                
            result["models_used"] = [self.model]
            return result
        except Exception as e:
            print(f"Vision Analysis failed: {e}")
            return {"error": f"Vision analysis failed: {str(e)}"}
