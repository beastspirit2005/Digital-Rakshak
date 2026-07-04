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

    async def execute(self, image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            return {"error": "Image file not found"}
            
        try:
            # We must open the file and pass it to the new genai SDK
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
                
            from google.genai import types
            
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp", "heic", "heif"] else "image/jpeg"
            
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[self.system_prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            result = json.loads(response.text)
            return result
        except Exception as e:
            return {"error": f"Vision analysis failed: {str(e)}"}
