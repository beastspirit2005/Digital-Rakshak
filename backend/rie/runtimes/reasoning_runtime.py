from typing import Any, Dict, List
from backend.shared.contracts.runtime import IReasoningRuntime
from infrastructure.ai.ollama_client import OllamaClient
import time
import logging

logger = logging.getLogger(__name__)

class RakshakReasoningRuntime(IReasoningRuntime):
    """
    Handles complex logical reasoning and explanation generation.
    Uses Local Ollama (Qwen) with a fallback to Groq if configured.
    """
    def __init__(self, ai_mode: str = "auto"):
        self._ai_mode = ai_mode
        self._is_loaded = True # Always assume loaded since Ollama is external service
        
    def load(self):
        pass

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload expects 'prompt' and optional 'context'
        """
        prompt = payload.get("prompt", "")
        context = payload.get("context", {})
        
        start_time = time.time()
        
        from core.config import settings
        resolved_mode = self._ai_mode if self._ai_mode != "auto" else settings.DEFAULT_AI_MODE
        
        try:
            if resolved_mode == "groq":
                from infrastructure.ai.groq_client import GroqClient
                client = GroqClient()
                result = await client.analyze(prompt, context=context, model_name="llama-3.1-8b-instant")
                engine = "Rakshak-Reasoning-Groq"
            else:
                client = OllamaClient()
                result = await client.analyze(prompt, context=context, model_name="qwen2.5:7b")
                engine = "Rakshak-Reasoning-Ollama"
                
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "response": result,
                "execution_time_ms": execution_time_ms,
                "engine": engine,
                "version": "latest"
            }
        except Exception as e:
            logger.error(f"Reasoning Runtime failed: {e}")
            raise

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy"}
