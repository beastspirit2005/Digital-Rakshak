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
        from infrastructure.ai.ml_client import ML_AVAILABLE
        
        if ML_AVAILABLE:
            # Run local GPU-accelerated inference
            result = self.client.predict(prompt)
        else:
            # Fallback to Groq for Vercel Serverless
            from infrastructure.ai.groq_client import GroqClient
            sys_prompt = "Classify this scam into ONE of these classes: 'Safe', 'Banking Fraud', 'UPI Fraud', 'Courier Scam', 'Digital Arrest', 'Counterfeit Note', 'Unknown Fraud'. Reply ONLY in JSON format: {\"threat_class\": \"<class>\", \"confidence\": 0.95}"
            groq = GroqClient()
            try:
                res = await groq.analyze(prompt, {"system": sys_prompt})
                import re
                json_match = re.search(r'\{.*\}', res.get("decision", ""), re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    result = {
                        "threat_class": parsed.get("threat_class", "Unknown Fraud"),
                        "confidence": float(parsed.get("confidence", 0.85))
                    }
                else:
                    result = {"threat_class": "Unknown Fraud", "confidence": 0.85}
            except Exception as e:
                logger.error(f"Groq classification failed: {e}")
                result = {"threat_class": "Unknown Fraud", "confidence": 0.50}

        engine_name = "Rakshak-Text" if ML_AVAILABLE else "Groq Llama-3 (Fallback)"
        
        return {
            "engine": engine_name,
            "engine_version": "1.0",
            "model_version": self.client.version,
            "entities": [],
            "evidence": [f"Scam mapped to TPR Class: {result.get('threat_class')}"],
            "reasoning": ["Calibrated confidence computed natively via Temperature Scaling." if ML_AVAILABLE else "Confidence provided by Groq Cloud."],
            "recommendation": ["Forward to BehaviourAgent for Attack DNA extraction."],
            "score": result.get('confidence', 0.85),
            "prompt_version": "n/a",
            "threat_class": result.get('threat_class', "Unknown Fraud")
        }

    def calculate_confidence(self, raw_score: float) -> float:
        return max(0.0, min(0.99, float(raw_score)))

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        pass
