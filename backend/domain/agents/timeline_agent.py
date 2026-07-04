from typing import Any, Dict
from domain.agents.base import BaseAgent
from domain.agents.router import AIRouter

class TimelineAgent(BaseAgent):
    """
    Timeline Intelligence Agent:
    Reconstructs the chronology of an attack from the raw text.
    """
    def __init__(self):
        super().__init__(agent_name="TimelineAgent", version="1.0")

    def initialize(self) -> None:
        self.router = AIRouter()
        self.prompt_template = """
        Extract a chronological timeline of events from this scam report.
        
        Report: {text}
        
        Respond ONLY with a JSON object:
        {{
            "score": 0.9,
            "decision": "Timeline Extracted",
            "evidence": [{{"finding": "Extracted 3 sequential events"}}]
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
        pass
