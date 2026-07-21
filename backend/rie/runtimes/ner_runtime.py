from typing import Any, Dict
from shared.contracts.runtime import INERRuntime
from infrastructure.ai.ml_client import RakshakNERClient
import time

class RakshakNERRuntime(INERRuntime):
    def __init__(self):
        self._model = RakshakNERClient(model_version="1.0")
        self._is_loaded = False
        
    def load(self):
        if not self._is_loaded:
            self._model.load_model()
            self._is_loaded = True

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.load()
        text = payload.get("text", "")
        
        start_time = time.time()
        entities = self._model.extract(text)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "entities": entities,
            "execution_time_ms": execution_time_ms,
            "engine": "Rakshak-NER-Runtime",
            "version": self._model.version
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._is_loaded else "unloaded"}
