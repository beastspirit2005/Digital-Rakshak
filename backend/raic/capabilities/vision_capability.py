from typing import Any, Dict
from shared.contracts.capability import ICapability
from shared.contracts.runtime import IVisionRuntime

class VisionCapability(ICapability):
    def __init__(self, runtime: IVisionRuntime):
        self._runtime = runtime

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        image_path = payload.get("image_path")
        if not image_path:
            raise ValueError("VisionCapability requires 'image_path' in payload.")
            
        runtime_result = await self._runtime.infer({
            "image_path": image_path,
            "analyze_type": payload.get("analyze_type", "scam")
        })
        
        res = runtime_result["result"]
        
        return {
            "decision": res.get("decision", "Unknown"),
            "confidence": res.get("score", res.get("confidence", 0.0)),
            "extracted_text": res.get("extracted_text", ""),
            "evidence": res.get("evidence", []),
            "execution_time_ms": runtime_result["execution_time_ms"],
            "metadata": {
                "engine": runtime_result["engine"],
                "version": runtime_result["version"]
            }
        }
