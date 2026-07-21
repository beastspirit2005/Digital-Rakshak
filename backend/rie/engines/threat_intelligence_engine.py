from typing import Any, Dict
from shared.contracts.engine import IEngine
from rie.runtime_registry import RuntimeRegistry

class ThreatIntelligenceEngine(IEngine):
    """
    Threat Intelligence Domain Engine.
    Uses ReasoningRuntime and potentially EmbeddingRuntime/NER to provide threat analysis.
    """
    def __init__(self, registry: RuntimeRegistry):
        self._registry = registry

    @property
    def engine_name(self) -> str:
        return "ThreatIntelligenceEngine"

    async def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError(f"{self.engine_name} requires 'text' in payload.")
            
        # Get the required runtime(s)
        reasoning_runtime = self._registry.get_runtime("reasoning_runtime")
        
        # Execute the runtime inference
        runtime_result = await reasoning_runtime.infer({"text": text})
        
        # Format the intelligence output
        return {
            "threat_class": runtime_result.get("threat_class", "UNKNOWN"),
            "confidence": runtime_result.get("confidence", 0.0),
            "execution_time_ms": runtime_result.get("execution_time_ms", 0),
            "metadata": {
                "engine": self.engine_name,
                "runtimes_used": ["reasoning_runtime"],
                "version": runtime_result.get("version", "unknown")
            }
        }
