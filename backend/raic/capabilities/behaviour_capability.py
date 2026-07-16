from typing import Any, Dict
from backend.shared.contracts.capability import ICapability
from backend.shared.contracts.runtime import IBehaviourRuntime

class BehaviourCapability(ICapability):
    def __init__(self, runtime: IBehaviourRuntime):
        self._runtime = runtime

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError("BehaviourCapability requires 'text' in payload.")
            
        runtime_result = await self._runtime.infer({"text": text})
        detected_behaviors = runtime_result["behaviors"]
        
        mitre_mapping = {
            "Impersonation": "T1566: Phishing (Impersonation)",
            "Urgency": "T1484: Domain Policy (Urgency/Pressure)",
            "Fear": "T1659: Content Injection (Fear/Intimidation)",
            "OTP Harvesting": "T1111: 2FA Interception",
            "Remote Access": "T1219: Remote Access Software"
        }
        mapped_behaviors = [mitre_mapping.get(b, b) for b in detected_behaviors]
        confidence = 0.90 if len(detected_behaviors) > 0 else 0.50
        
        return {
            "behaviors": mapped_behaviors,
            "raw_behaviors": detected_behaviors,
            "confidence": confidence,
            "execution_time_ms": runtime_result["execution_time_ms"],
            "metadata": {
                "engine": runtime_result["engine"],
                "version": runtime_result["version"]
            }
        }
