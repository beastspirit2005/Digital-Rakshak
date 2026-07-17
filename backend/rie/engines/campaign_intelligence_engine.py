from typing import Any, Dict
from backend.shared.contracts.engine import IEngine
from backend.rie.runtime_registry import RuntimeRegistry

class CampaignIntelligenceEngine(IEngine):
    def __init__(self, registry: RuntimeRegistry):
        self._registry = registry

    @property
    def engine_name(self) -> str:
        return "CampaignIntelligenceEngine"

    async def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError(f"{self.engine_name} requires 'text' in payload.")
            
        # Mocking campaign runtime for now or using reasoning
        try:
            runtime = self._registry.get_runtime("reasoning_runtime")
            runtime_result = await runtime.infer({"text": f"Campaign Analysis: {text}"})
        except ValueError:
            runtime_result = {"campaign_name": "UNKNOWN_CAMPAIGN", "confidence": 0.5, "execution_time_ms": 100}
        
        return {
            "campaign_name": runtime_result.get("campaign_name", "UNKNOWN_CAMPAIGN"),
            "confidence": runtime_result.get("confidence", 0.0),
            "execution_time_ms": runtime_result.get("execution_time_ms", 0),
            "metadata": {
                "engine": self.engine_name,
                "runtimes_used": ["reasoning_runtime"],
            }
        }
