from typing import Any, Dict
from backend.shared.contracts.runtime import IVisionRuntime
import time
import os

class RakshakVisionRuntime(IVisionRuntime):
    def __init__(self):
        self._is_loaded = False
        
    def load(self):
        # Dummy load for vision dependencies
        if not self._is_loaded:
            self._is_loaded = True

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.load()
        image_path = payload.get("image_path", "")
        analyze_type = payload.get("analyze_type", "scam")
        
        start_time = time.time()
        
        if analyze_type == "counterfeit":
            from infrastructure.ai.ml_client import RakshakVisionClient
            client = RakshakVisionClient()
            client.load_model()
            result = client.detect_counterfeit(image_path)
            engine = "Rakshak-Counterfeit-MobileNetV3"
        else:
            from infrastructure.ai.ml_client import RakshakVisionClient
            client = RakshakVisionClient()
            client.load_model()
            extracted = client.extract_text(image_path)
            result = {
                "decision": "Manual Review Required (Offline OCR)",
                "score": 0.5,
                "extracted_text": extracted,
                "evidence": ["Image analyzed via offline EasyOCR."]
            }
            engine = "Rakshak-Vision-OCR"

        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "result": result,
            "execution_time_ms": execution_time_ms,
            "engine": engine,
            "version": "1.0"
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._is_loaded else "unloaded"}
