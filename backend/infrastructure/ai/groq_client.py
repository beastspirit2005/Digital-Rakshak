import os
import json
import httpx
from typing import Dict, Any
from core.config import settings

class GroqClient:
    """
    Client for Groq LPU inference using the OpenAI compatible endpoint.
    Provides extremely fast intelligence generation.
    """
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.default_model = "llama-3.3-70b-versatile"

    async def analyze(self, prompt: str, context: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
        """
        Sends a prompt and context to Groq for analysis.
        Enforces a strict JSON Schema output.
        """
        model = model_name or self.default_model
        
        full_prompt = f"""
        You are an elite cyber threat intelligence AI.
        Analyze the following context and prompt. 
        You MUST return your response in raw JSON format EXACTLY matching this schema with NO OTHER TEXT:
        {{
            "decision": "Your final verdict",
            "score": 0.8,
            "evidence": [{{"relevance": "string"}}],
            "estimated_latitude": 19.0760,
            "estimated_longitude": 72.8777,
            "phone_numbers": ["9999988888"],
            "urls": ["http://scam.com"],
            "upi_ids": ["scammer@ybl"],
            "bank_accounts": ["123456789"]
        }}

        Prompt: {prompt}
        Context: {json.dumps(context)}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                if "choices" not in data or not data["choices"]:
                    raise ValueError(f"Unexpected Groq response: {data}")
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                
                # Ensure required keys exist
                if "score" not in result:
                    result["score"] = 0.5
                if "decision" not in result:
                    result["decision"] = "Error parsing decision"
                if "evidence" not in result:
                    result["evidence"] = []
                    
                result["models"] = [model]
                result["prompt_version"] = "v1.0"
                return result
                
        except Exception as e:
            print(f"Groq API Error: {e}")
            return {
                "decision": f"Groq API Error: {str(e)}",
                "score": 0.0,
                "evidence": [],
                "models": [model],
                "prompt_version": "v1.0"
            }

    async def generate_text(self, prompt: str, model_name: str = None) -> str:
        """
        Sends a raw prompt to Groq for a conversational or unstructured text response.
        """
        model = model_name or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                if "choices" not in data or not data["choices"]:
                    return "Groq Inference Error: Unexpected API response structure."
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq API Error (generate_text): {e}")
            return f"Groq Inference Error: {str(e)}"

    async def transcribe_audio(self, audio_file_path: str) -> dict:
        """
        Sends an audio file to Groq's Whisper API for transcription.
        """
        import os
        import mimetypes
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        if not os.path.exists(audio_file_path):
            return {"error": "Audio file not found."}
            
        try:
            mime_type, _ = mimetypes.guess_type(audio_file_path)
            if not mime_type:
                mime_type = "audio/webm" if audio_file_path.endswith(".webm") else "audio/mpeg"
                
            async with httpx.AsyncClient() as client:
                with open(audio_file_path, "rb") as f:
                    files = {
                        "file": (os.path.basename(audio_file_path), f, mime_type)
                    }
                    data = {
                        "model": "whisper-large-v3"
                    }
                    response = await client.post(url, headers=headers, data=data, files=files, timeout=60.0)
                    response.raise_for_status()
                    result = response.json()
                    return {"transcript": result.get("text", ""), "source": "groq_whisper"}
        except Exception as e:
            print(f"Groq Audio API Error: {e}")
            return {"error": f"Groq Audio API Error: {str(e)}"}
