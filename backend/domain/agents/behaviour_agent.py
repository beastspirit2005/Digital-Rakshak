from typing import Any, Dict
from domain.agents.base import BaseAgent
from infrastructure.ai.ml_client import RakshakCoreClient
import logging

logger = logging.getLogger(__name__)

class BehaviourAgent(BaseAgent):
    """
    Extracts Attack DNA and Social Engineering behaviors from text.
    Powered by Rakshak-Behaviour (Multi-label head of RakshakCoreClient).
    """

    def __init__(self, agent_name="BehaviourAgent", version="1.0"):
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
        result = self.client.predict(prompt)
        
        detected_behaviors = result['behaviors']
        confidence = 0.90 if len(detected_behaviors) > 0 else 0.50
        
        return {
            "engine": "Rakshak-Behaviour",
            "engine_version": "1.0",
            "model_version": self.client.version,
            "entities": [],
            "evidence": detected_behaviors,
            "reasoning": [f"Detected {len(detected_behaviors)} social engineering indicators."],
            "recommendation": ["Pass Attack DNA to CampaignAgent for embedding matching."],
            "score": confidence,
            "prompt_version": "n/a"
        }

    def calculate_confidence(self, raw_score: float) -> float:
        return max(0.0, min(1.0, float(raw_score)))

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        pass
