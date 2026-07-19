import os
import json
import re
import base64
from typing import Dict, Any, Optional
from core.config import settings

# Vision model on Groq that supports image input (confirmed via /v1/models)
GROQ_VISION_MODEL = "qwen/qwen3.6-27b"
GEMINI_VISION_MODEL = "gemini-2.0-flash"  # Google fallback (requires GOOGLE_API_KEY)

class VisionAgent:
    """
    Analyzes screenshots and image evidence to detect digital fraud.
    Primary: Groq Qwen 3.6 27B (vision-capable, supports image input).
    Fallback: Google Gemini Flash if GOOGLE_API_KEY is set.
    Last resort: Graceful degradation (manual review message, no 500 crash).
    """

    def __init__(self):
        self.model = GROQ_VISION_MODEL
        self.system_prompt = """You are an elite Cyber Threat Intelligence Vision AI.
Analyze the provided image (screenshot of a WhatsApp chat, bank transfer, email, etc.) for signs of a scam or digital fraud.
You MUST extract any text in the image.
Respond ONLY with raw JSON (no markdown, no code fences) matching this exact schema:
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
        analyze_type = payload.get("analyze_type", "scam").lower()  # 'scam' or 'counterfeit'

        if not os.path.exists(image_path):
            return {"error": "Image file not found"}

        resolved_mode = ai_mode if ai_mode != "auto" else settings.DEFAULT_AI_MODE

        # OFFLINE MODE (Local PyTorch) — with auto-fallback to Cloud if PyTorch unavailable
        if resolved_mode == "ollama" or settings.FORCE_LOCAL_INFERENCE:
            try:
                if analyze_type == "counterfeit":
                    from infrastructure.ai.ml_client import RakshakVisionClient, ML_AVAILABLE
                    if not ML_AVAILABLE:
                        raise ImportError("PyTorch not available in this environment")
                    client = RakshakVisionClient()
                    client.load_model()
                    if not client.model_loaded:
                        raise RuntimeError("Counterfeit model not loaded")
                    return client.detect_counterfeit(image_path)
                else:
                    from infrastructure.ai.ml_client import RakshakVisionClient, ML_AVAILABLE
                    if not ML_AVAILABLE:
                        raise ImportError("PyTorch not available in this environment")
                    client = RakshakVisionClient()
                    client.load_model()
                    extracted = client.extract_text(image_path)
                    return {
                        "decision": "Manual Review Required (Offline OCR)",
                        "score": 0.5,
                        "extracted_text": extracted,
                        "evidence": ["Image analyzed via offline EasyOCR."]
                    }
            except (ImportError, RuntimeError) as e:
                print(f"Local inference unavailable ({e}), falling back to Cloud...")

        # CLOUD MODE: Groq Qwen 3.6 27B (confirmed vision-capable on Groq)
        try:
            result = await self._analyze_with_groq_vision(image_path, analyze_type)
            result["models_used"] = [GROQ_VISION_MODEL]
            return result
        except Exception as e:
            print(f"Groq vision failed ({e}), trying Gemini fallback...")

        # FALLBACK: Google Gemini Flash (requires GOOGLE_API_KEY in env)
        google_api_key = getattr(settings, "GOOGLE_API_KEY", None)
        if google_api_key:
            try:
                result = await self._analyze_with_gemini(image_path, analyze_type, google_api_key)
                result["models_used"] = [GEMINI_VISION_MODEL]
                return result
            except Exception as e:
                print(f"Gemini vision also failed ({e})")

        # GRACEFUL DEGRADATION — return structured response, never crash with 500
        print("All vision providers failed, returning manual review response")
        return {
            "decision": "Manual Review Required — Vision AI Unavailable",
            "score": 0.0,
            "threat_class": "Unknown",
            "evidence": ["Automated vision analysis is currently unavailable. Please review the image manually."],
            "models_used": []
        }

    async def _analyze_with_groq_vision(self, image_path: str, analyze_type: str) -> Dict[str, Any]:
        """Analyze image using Groq Qwen 3.6 27B (supports image input modality)."""
        import httpx

        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower().replace(".", "")
        mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp"] else "image/jpeg"

        if analyze_type == "counterfeit":
            prompt = """You are an elite Currency Authentication AI.
Analyze the provided image of a currency note for signs of it being counterfeit (fake).
Check for watermarks, security threads, intaglio printing, and micro-lettering if visible.
Respond ONLY with raw JSON (no markdown, no code fences) matching this exact schema:
{"decision": "Counterfeit Currency Detected" or "Genuine Currency", "score": 0.0, "threat_class": "Counterfeit Note", "evidence": ["anomalies found"]}"""
        else:
            prompt = self.system_prompt

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload_data = {
            "model": GROQ_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload_data, timeout=60.0
            )
            if response.status_code != 200:
                raise RuntimeError(f"Groq API Error {response.status_code}: {response.text[:300]}")
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        print(f"Raw Groq Vision Response: {content[:300]}")

        # Strip <think>...</think> blocks from reasoning models even if they are unclosed
        content = re.sub(r"<think>.*?(?:</think>|$)", "", content, flags=re.DOTALL).strip()
        # Strip markdown code fences
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            result_raw = json.loads(content)
            return {k.lower(): v for k, v in result_raw.items()}
        except json.JSONDecodeError:
            return {
                "decision": "Error parsing AI response",
                "score": 0.0,
                "threat_class": "Unknown",
                "evidence": [f"Raw AI output: {content[:300]}"]
            }

    async def _analyze_with_gemini(self, image_path: str, analyze_type: str, api_key: str) -> Dict[str, Any]:
        """Analyze image using Google Gemini Flash (supports vision)."""
        import httpx

        with open(image_path, "rb") as f:
            image_bytes = f.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower().replace(".", "")
        mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp", "gif"] else "image/jpeg"

        if analyze_type == "counterfeit":
            prompt = """You are an elite Currency Authentication AI.
Analyze the provided image of a currency note for signs of it being counterfeit (fake).
Check for watermarks, security threads, intaglio printing, and micro-lettering if visible.
Respond ONLY with raw JSON (no markdown, no code fences) matching this exact schema:
{"decision": "Counterfeit Currency Detected" or "Genuine Currency", "score": 0.0, "threat_class": "Counterfeit Note", "evidence": ["anomalies found"]}"""
        else:
            prompt = self.system_prompt + "\nRespond ONLY with raw JSON, no markdown fences."

        gemini_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": base64_image}}
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_VISION_MODEL}:generateContent?key={api_key}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=gemini_payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates (content may be blocked)")
        parts = candidates[0].get("content", {}).get("parts", [{}])
        content = parts[0].get("text", "") if parts else ""
        print(f"Raw Gemini Response: {content[:300]}")

        # Strip <think>...</think> blocks for Gemini as well
        content = re.sub(r"<think>.*?(?:</think>|$)", "", content, flags=re.DOTALL).strip()
        
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            result_raw = json.loads(content)
            return {k.lower(): v for k, v in result_raw.items()}
        except json.JSONDecodeError:
            return {
                "decision": "Analysis Complete (parse error)",
                "score": 0.5,
                "threat_class": "Unknown",
                "evidence": [f"Raw AI output: {content[:300]}"]
            }
