from typing import Dict, Any
from infrastructure.ai.gemini_client import GeminiClient
from infrastructure.ai.ollama_client import OllamaClient
from core.config import settings

class AIRouter:
    """
    Intelligent Router for handling Hybrid AI Execution.
    Routes to Gemini by default for high-reasoning, falls back to Ollama if local/privacy is enforced
    or if the cloud API is down.
    """
    
    def __init__(self):
        self.gemini = GeminiClient()
        self.ollama = OllamaClient()
        
    async def execute(self, prompt: str, context: Dict[str, Any], require_local: bool = False, ai_mode: str = "auto") -> Dict[str, Any]:
        """
        Executes the prompt against the appropriate LLM engine based on configuration
        and the privacy requirements of the task.
        """
        import asyncio
        
        # Parse ai_mode to check if a specific model was requested
        engine = "auto"
        model_override = None
        if ":" in ai_mode:
            parts = ai_mode.split(":", 1)
            engine = parts[0]
            model_override = parts[1]
        else:
            engine = ai_mode

        # If engine is auto, read the live default preference from the admin settings
        if engine == "auto":
            from api.v1.settings import get_default_ai_mode
            engine = get_default_ai_mode()

        # If the task requires local execution (e.g., highly sensitive PII), force Ollama
        if require_local or settings.FORCE_LOCAL_INFERENCE or engine == "ollama":
            return await self.ollama.analyze(prompt, context, model_name=model_override)
            
        if engine == "both":
            # Run both in parallel
            gemini_task = asyncio.create_task(self.gemini.analyze(prompt, context))
            ollama_task = asyncio.create_task(self.ollama.analyze(prompt, context))
            
            gemini_res, ollama_res = await asyncio.gather(gemini_task, ollama_task, return_exceptions=True)
            
            # Combine results
            combined = {
                "decision": f"Gemini: {gemini_res.get('decision', 'Error') if isinstance(gemini_res, dict) else 'Error'} | Ollama: {ollama_res.get('decision', 'Error') if isinstance(ollama_res, dict) else 'Error'}",
                "score": max(
                    gemini_res.get("score", 0.0) if isinstance(gemini_res, dict) else 0.0,
                    ollama_res.get("score", 0.0) if isinstance(ollama_res, dict) else 0.0
                ),
                "evidence": (gemini_res.get("evidence", []) if isinstance(gemini_res, dict) else []) + 
                            (ollama_res.get("evidence", []) if isinstance(ollama_res, dict) else []),
                "models": ["gemini", "ollama"],
                "estimated_latitude": None,
                "estimated_longitude": None
            }
            # Grab coordinates from whichever provided them
            if isinstance(gemini_res, dict) and gemini_res.get("estimated_latitude"):
                combined["estimated_latitude"] = gemini_res["estimated_latitude"]
                combined["estimated_longitude"] = gemini_res["estimated_longitude"]
            elif isinstance(ollama_res, dict) and ollama_res.get("estimated_latitude"):
                combined["estimated_latitude"] = ollama_res["estimated_latitude"]
                combined["estimated_longitude"] = ollama_res["estimated_longitude"]
                
            return combined
            
        # Default ("auto" or "gemini") try Gemini first for superior reasoning capability
        try:
            result = await self.gemini.analyze(prompt, context, model_name=model_override)
            if isinstance(result, dict) and "Gemini API Error" in result.get("decision", ""):
                print("Gemini failed, falling back to Ollama...")
                return await self.ollama.analyze(prompt, context)
            return result
        except Exception as e:
            print(f"Unhandled Gemini exception: {e}, falling back to Ollama...")
            return await self.ollama.analyze(prompt, context)
