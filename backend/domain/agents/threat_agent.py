import json
from typing import Any, Dict
from domain.agents.base import BaseAgent
from infrastructure.ai.ml_client import RakshakCoreClient
from infrastructure.event_bus.catalog import EventCatalog
import logging
import time

logger = logging.getLogger(__name__)

class ThreatAnalysisAgent(BaseAgent):
    """
    Analyzes raw text (SMS, WhatsApp, Email) to classify scams and extract entities.
    Powered by Rakshak-Text (Local PyTorch Multi-Task Model).
    """

    def __init__(self, agent_name="ThreatAnalysisAgent", version="1.0"):
        super().__init__(agent_name, version)

    def initialize(self) -> None:
        self.client = RakshakCoreClient(model_version="1.0")
        self.client.load_model()

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        return "text" in payload

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        return {}

    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Run local GPU-accelerated inference
        result = self.client.predict(prompt)
        
        return {
            "engine": "Rakshak-Text",
            "engine_version": "1.0",
            "model_version": self.client.version,
            "entities": [],
            "evidence": [f"Scam mapped to TPR Class: {result['threat_class']}"],
            "reasoning": ["Calibrated confidence computed natively via Temperature Scaling."],
            "recommendation": ["Forward to BehaviourAgent for Attack DNA extraction."],
            "score": result['confidence'],
            "prompt_version": "n/a", # No prompts needed for custom models
            "threat_class": result['threat_class']
        }

    def calculate_confidence(self, raw_score: float) -> float:
        return max(0.0, min(0.99, float(raw_score)))

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        pass
