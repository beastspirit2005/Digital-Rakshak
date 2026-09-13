import json
from typing import Dict, Any
import ollama
from core.config import settings

LEGACY_MODEL_MAP = {
    "mistral": "llama3:8b",
    "qwen2.5:7b": "llama3:8b",
    "qwen2.5": "llama3:8b",
    "mistral:7b": "llama3:8b"
}

class OllamaClient:
    """
    Client for Local Ollama inference.
    Used for privacy-sensitive tasks, basic embeddings, and fallback reasoning.
    """
    
    def __init__(self):
        self.default_model = getattr(settings, "OLLAMA_MODEL", "llama3:8b")
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)

    def _resolve_model(self, model_name: str = None) -> str:
        if not model_name:
            return self.default_model
        return LEGACY_MODEL_MAP.get(model_name, model_name)

    async def analyze(self, prompt: str, context: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
        """
        Sends a prompt and JSON context to local Ollama.
        """
        model = self._resolve_model(model_name)
        
        full_prompt = f"""
        You are an elite cyber threat intelligence AI.
        Analyze the following context and prompt. 
        You MUST return your response in raw JSON format with the following schema:
        {{
            "decision": "Your final verdict",
            "score": float between 0.0 and 1.0,
            "evidence": [{{"relevance": "string"}}],
            "estimated_latitude": float (or null if unknown),
            "estimated_longitude": float (or null if unknown)
        }}

        Prompt: {prompt}
        Context: {json.dumps(context)}
        """

        try:
            response = await self.client.chat(
                model=model,
                messages=[
                    {'role': 'user', 'content': full_prompt}
                ],
                format='json',
                options={
                    'temperature': 0.2
                }
            )
            
            # The response message content should be a valid JSON string
            if not hasattr(response, 'message') or not hasattr(response.message, 'content') or not response.message.content:
                raise ValueError(f"Unexpected Ollama response: {response}")
            result = json.loads(response.message.content)
            
            # Ensure required keys exist
            if "score" not in result:
                result["score"] = 0.5
            if "decision" not in result:
                result["decision"] = "Error parsing decision"
            if "evidence" not in result:
                result["evidence"] = []
                
            result["models"] = [f"ollama-{model}"]
            result["prompt_version"] = "v1.0"
            return result
            
        except Exception as e:
            print(f"Ollama API Error: {e}")
            if 'response' in locals():
                print(f"Raw Ollama Response: {response}")
            return {
                "decision": f"Ollama Inference Error: {str(e)}",
                "score": 0.0,
                "evidence": [],
                "models": [f"ollama-{model}"],
                "prompt_version": "v1.0"
            }

    async def generate_text(self, prompt: str, model_name: str = None) -> str:
        """
        Sends a raw prompt to Ollama for a conversational or unstructured text response.
        """
        model = self._resolve_model(model_name)
        try:
            response = await self.client.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.4}
            )
            if not hasattr(response, 'message') or not hasattr(response.message, 'content') or not response.message.content:
                return "Ollama Inference Error: Unexpected API response structure."
            return response.message.content
        except Exception as e:
            print(f"Ollama API Error (generate_text): {e}")
            return f"Ollama Inference Error: {str(e)}"
