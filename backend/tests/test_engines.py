import pytest
import asyncio
from backend.rie.engines.threat_intelligence_engine import ThreatIntelligenceEngine
from backend.rie.runtime_registry import RuntimeRegistry
from backend.shared.contracts.runtime import IRuntime
from typing import Dict, Any

class MockReasoningRuntime(IRuntime):
    def __init__(self):
        self.invoked = False
        
    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.invoked = True
        return {
            "threat_class": "PHISHING",
            "confidence": 0.95,
            "execution_time_ms": 120,
            "version": "1.0-mock"
        }
        
    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

@pytest.mark.asyncio
async def test_threat_intelligence_engine():
    registry = RuntimeRegistry()
    mock_runtime = MockReasoningRuntime()
    registry.register_runtime("reasoning_runtime", mock_runtime)
    
    engine = ThreatIntelligenceEngine(registry)
    
    payload = {"text": "Click here to win a million dollars"}
    result = await engine.analyze(payload)
    
    assert mock_runtime.invoked is True
    assert result["threat_class"] == "PHISHING"
    assert result["confidence"] == 0.95
    assert result["metadata"]["engine"] == "ThreatIntelligenceEngine"
    assert "reasoning_runtime" in result["metadata"]["runtimes_used"]
