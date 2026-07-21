from typing import Any, Dict
from shared.contracts.engine import IEngine
from rie.runtime_registry import RuntimeRegistry

class BehaviourIntelligenceEngine(IEngine):
    """
    Behaviour Intelligence Domain Engine.
    Uses ReasoningRuntime or BehaviourRuntime to provide behavioural analysis.
    """
    def __init__(self, registry: RuntimeRegistry):
        self._registry = registry

    @property
    def engine_name(self) -> str:
        return "BehaviourIntelligenceEngine"

    async def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError(f"{self.engine_name} requires 'text' in payload.")
            
        behaviour_runtime = self._registry.get_runtime("behaviour_runtime")
        
        runtime_result = await behaviour_runtime.infer({"text": text})
        
        return {
            "behaviour_flags": runtime_result.get("flags", []),
            "confidence": runtime_result.get("confidence", 0.0),
            "execution_time_ms": runtime_result.get("execution_time_ms", 0),
            "metadata": {
                "engine": self.engine_name,
                "runtimes_used": ["behaviour_runtime"],
                "version": runtime_result.get("version", "unknown")
            }
        }
