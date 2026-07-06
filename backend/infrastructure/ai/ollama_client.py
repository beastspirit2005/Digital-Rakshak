import json
from typing import Dict, Any
import ollama

class OllamaClient:
    """
    Client for Local Ollama inference.
    Used for privacy-sensitive tasks, basic embeddings, and fallback reasoning.
    """
    
    def __init__(self):
        # We assume Ollama is running locally (e.g. via Docker or native service)
        # on the default port 11434. The ollama SDK connects there by default.
        self.default_model = "mistral" # 7B quantized model fits in 8GB VRAM
        self.client = ollama.AsyncClient()

    async def analyze(self, prompt: str, context: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
        """
        Sends a prompt and JSON context to local Ollama.
        """
        model = model_name or self.default_model
        
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
            result = json.loads(response['message']['content'])
            
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
        model = model_name or self.default_model
        try:
            response = await self.client.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.4}
            )
            return response['message']['content']
        except Exception as e:
            print(f"Ollama API Error (generate_text): {e}")
            return f"Ollama Inference Error: {str(e)}"
