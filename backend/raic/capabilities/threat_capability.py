from typing import Any, Dict
from backend.shared.contracts.capability import ICapability
from backend.shared.contracts.runtime import IThreatRuntime

class ThreatCapability(ICapability):
    """
    Decouples the Threat Agent from the underlying runtime.
    Handles data validation and transformation.
    """
    def __init__(self, runtime: IThreatRuntime):
        self._runtime = runtime

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError("ThreatCapability requires 'text' in payload.")
            
        # Execute the runtime inference
        runtime_result = await self._runtime.infer({"text": text})
        
        # Standardize the output for the RAIC agent
        return {
            "threat_class": runtime_result["threat_class"],
            "confidence": runtime_result["confidence"],
            "execution_time_ms": runtime_result["execution_time_ms"],
            "metadata": {
                "engine": runtime_result["engine"],
                "version": runtime_result["version"]
            }
        }
