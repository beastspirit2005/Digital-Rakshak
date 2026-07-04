from typing import Any, Dict
from domain.agents.base import BaseAgent
from domain.agents.router import AIRouter

class GeoAgent(BaseAgent):
    """
    Geospatial Intelligence Agent:
    Interfaces with PostGIS to detect spatial anomalies and containment zones.
    """
    def __init__(self):
        super().__init__(agent_name="GeoAgent", version="1.0")

    def initialize(self) -> None:
        self.router = AIRouter()
        self.prompt_template = """
        Analyze these spatial coordinates and the scam type to determine containment risk.
        
        Location: {lat}, {lng}
        Scam Type: {scam_type}
        
        Respond ONLY with a JSON object:
        {{
            "score": 0.8,
            "decision": "High Spatial Risk",
            "evidence": [{{"finding": "Urban density increases physical scam spread"}}]
        }}
        """

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        return "latitude" in payload and "longitude" in payload

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        return {}

    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ai_mode = context.get("ai_mode", "auto")
        # In a real system, we'd run PostGIS queries here first.
        full_prompt = self.prompt_template.format(
            lat=context.get("latitude", 0), 
            lng=context.get("longitude", 0),
            scam_type=context.get("scam_type", "Unknown")
        )
        return await self.router.execute(prompt=full_prompt, context=context, ai_mode=ai_mode)

    def calculate_confidence(self, raw_score: float) -> float:
        return min(max(raw_score, 0.0), 1.0)

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        pass
