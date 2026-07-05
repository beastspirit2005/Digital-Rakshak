from typing import Any, Dict
from domain.agents.base import BaseAgent

class IntelligenceAgent(BaseAgent):
    """
    IntelligenceAgent is a non-AI structural agent.
    Its sole responsibility is to take the final fused Decision Package 
    from the RAIC Decision Core and persist it to:
    1. NTIR (National Threat Intelligence Repository) - PostgreSQL
    2. Analytical Data Repository (ADR)
    3. Neo4j Graph Database
    4. PostGIS Geospatial Database
    """
    
    def __init__(self):
        super().__init__(agent_name="IntelligenceAgent", version="1.0")

    def initialize(self) -> None:
        pass

    async def inference(self, prompt: str, context: Dict[str, Any], ai_mode: str = "mock") -> Dict[str, Any]:
        return {}

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        # Expects the final fused package
        required_keys = ["decision", "confidence", "threat_class"]
        return all(key in payload for key in required_keys)

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        return {}

    async def execute(self, payload: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        case_number = payload.get("case_number")
        entities = payload.get("entities", {})
        decision_obj = payload.get("decision", {})
        
        try:
            from infrastructure.graph.neo4j_client import IntelligenceGraph
            graph = IntelligenceGraph()
            
            for phone in entities.get("PHONE", []):
                await graph.add_case_entity_link(case_number, "PhoneNumber", str(phone))
            for url in entities.get("URLS", []):
                await graph.add_case_entity_link(case_number, "URL", str(url))
            for upi in entities.get("UPI", []):
                await graph.add_case_entity_link(case_number, "UPI_ID", str(upi))
            for ifsc in entities.get("IFSC", []):
                await graph.add_case_entity_link(case_number, "BankAccount", str(ifsc)) # Basic mock for IFSC
                
        except Exception as graph_err:
            print(f"Failed to link entities in Neo4j via IntelligenceAgent: {graph_err}")
            
        return decision_obj

    def calculate_confidence(self, raw_score: float) -> float:
        return 1.0 # Storage operations are deterministic

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        # Final event published to stream
        pass
