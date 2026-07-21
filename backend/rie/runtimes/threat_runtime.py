from typing import Any, Dict
from shared.contracts.runtime import IThreatRuntime
from infrastructure.ai.ml_client import RakshakCoreClient
import time

class RakshakThreatRuntime(IThreatRuntime):
    """
    Concrete implementation of the Threat Runtime.
    Manages the lifecycle and execution of the local Rakshak-Text PyTorch model.
    """
    def __init__(self):
        self._model = RakshakCoreClient(model_version="1.0")
        self._is_loaded = False
        
    def load(self):
        if not self._is_loaded:
            self._model.load_model()
            self._is_loaded = True

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects payload with 'text' to analyze.
        """
        self.load()
        text = payload.get("text", "")
        
        start_time = time.time()
        result = self._model.predict(text)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "threat_class": result.get("threat_class", "Safe"),
            "confidence": result.get("confidence", 0.0),
            "execution_time_ms": execution_time_ms,
            "engine": "Rakshak-Text-Runtime",
            "version": self._model.version
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self._is_loaded else "unloaded",
            "model_version": self._model.version,
            "gpu_allocated": False # Placeholder until hardware metrics added
        }
