from typing import Any, Dict
from domain.agents.base import BaseAgent
from domain.agents.router import AIRouter

class BehaviourAgent(BaseAgent):
    """
    Analyzes scam text to extract 'Attack DNA':
    - Psychological manipulation techniques (Urgency, Authority)
    - Attack methodology
    - Social engineering patterns
    """
    def __init__(self):
        super().__init__(agent_name="BehaviourAgent", version="1.0")

    def initialize(self) -> None:
        self.router = AIRouter()
        self.prompt_template = """
        Analyze this cybercrime report and extract the 'Attack DNA' (behavioral fingerprint).
        Focus on psychological manipulation, attack methodology, and social engineering.
        
        Report:
        {text}
        
        Respond ONLY with a JSON object in this exact format:
        {{
            "score": 0.8,
            "decision": "Social Engineering Detected",
            "evidence": [{{"finding": "used urgent language"}}],
            "attack_dna": {{
                "urgency_level": "high",
                "authority_impersonation": "police",
                "manipulation_techniques": ["fear", "time pressure"],
                "scam_type_code": "DIGITAL_ARREST"
            }}
        }}
        """

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        return "text" in payload and bool(payload["text"])

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        return {}

    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ai_mode = context.get("ai_mode", "auto")
        full_prompt = self.prompt_template.format(text=prompt)
        
        return await self.router.execute(prompt=full_prompt, context=context, ai_mode=ai_mode)

    def calculate_confidence(self, raw_score: float) -> float:
        return min(max(raw_score, 0.0), 1.0)

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        # Event bus not yet implemented, pass for now
        pass
