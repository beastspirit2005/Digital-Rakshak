from typing import Any, Dict
from backend.shared.contracts.runtime import IBehaviourRuntime
from infrastructure.ai.ml_client import RakshakCoreClient
import time

class RakshakBehaviourRuntime(IBehaviourRuntime):
    def __init__(self):
        self._model = RakshakCoreClient(model_version="1.0")
        self._is_loaded = False
        
    def load(self):
        if not self._is_loaded:
            self._model.load_model()
            self._is_loaded = True

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.load()
        text = payload.get("text", "")
        
        start_time = time.time()
        result = self._model.predict(text)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "behaviors": result.get("behaviors", []),
            "execution_time_ms": execution_time_ms,
            "engine": "Rakshak-Behaviour-Runtime",
            "version": self._model.version
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._is_loaded else "unloaded"}
