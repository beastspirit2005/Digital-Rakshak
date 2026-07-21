from typing import Any, Dict
from shared.contracts.capability import ICapability
from shared.contracts.runtime import IVoiceRuntime

class VoiceCapability(ICapability):
    def __init__(self, runtime: IVoiceRuntime):
        self._runtime = runtime

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = payload.get("audio_path")
        if not audio_path:
            raise ValueError("VoiceCapability requires 'audio_path' in payload.")
            
        runtime_result = await self._runtime.infer({"audio_path": audio_path})
        
        transcript = runtime_result["transcript"]
        confidence = 0.95 if transcript else 0.0
        
        return {
            "transcript": transcript,
            "confidence": confidence,
            "execution_time_ms": runtime_result["execution_time_ms"],
            "metadata": {
                "engine": runtime_result["engine"],
                "version": runtime_result["version"]
            }
        }
