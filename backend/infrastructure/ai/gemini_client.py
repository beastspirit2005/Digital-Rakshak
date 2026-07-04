import os
import json
from typing import Dict, Any, List
from google import genai
from google.genai import types
from core.config import settings

class GeminiClient:
    """
    Client for Google Gemini using the new google-genai SDK.
    Used for high-reasoning tasks and multimodal inputs.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})
        self.default_model = "gemini-2.0-flash"

    async def analyze(self, prompt: str, context: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
        """
        Sends a prompt and context to Gemini for analysis.
        Enforces a strict JSON Schema output.
        """
        model = model_name or "gemini-1.5-flash"
        
        # We merge the context into the prompt text to provide Gemini the necessary data
        full_prompt = f"""
        You are an elite cyber threat intelligence AI.
        Analyze the following context and prompt. 
        You MUST return your response in raw JSON format with the following schema:
        {{
            "decision": "Your final verdict",
            "score": float between 0.0 and 1.0,
            "evidence": [{"relevance": "string"}],
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

        try:
            # Call Gemini via async method
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2, # Low temperature for more deterministic analysis
                ),
            )
            
            # The response text should be a valid JSON string
            result = json.loads(response.text)
            
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
            print(f"Gemini API Error: {e}")
            return {
                "decision": f"Gemini API Error: {str(e)}",
                "score": 0.0,
                "evidence": [],
                "models": [model],
                "prompt_version": "v1.0"
            }
