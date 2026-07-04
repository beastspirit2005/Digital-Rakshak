import json
import asyncio
from typing import Dict, Any, Optional
from domain.agents.router import AIRouter

class FusionAgent:
    """
    The orchestrator. Takes the outputs from the specialized agents,
    and merges them into a single, cohesive JSON verdict.
    """
    
    def __init__(self):
        self.router = AIRouter()
        self.system_prompt = """You are the Supreme Commander of the RAIC (Routing AI Coordinator) Core.
You are receiving intelligence reports from specialized sub-agents:
1. Core Text Agent (analyzed the user's text description)
2. Vision/Audio Agents (if evidence was provided)
3. Behaviour Agent (extracted Attack DNA)
4. Knowledge Agent (regulatory context)
5. Timeline Agent (attack chronology)
6. Recommendation Agent (suggested actions)

Consolidate their findings into ONE final verdict.
Your JSON output MUST match this exact schema:
{
    "decision": "Scam or Safe with comprehensive reasoning",
    "score": 0.5,
    "estimated_latitude": 0.0,
    "estimated_longitude": 0.0,
    "phone_numbers": ["unique strings"],
    "urls": ["unique strings"],
    "upi_ids": ["unique strings"],
    "bank_accounts": ["unique strings"],
    "evidence_types_processed": ["text", "image"],
    "attack_dna": {"urgency": "...", "type": "..."},
    "timeline": ["event 1", "event 2"],
    "regulatory_context": ["RBI circular X"],
    "recommended_actions": ["freeze X", "block Y"]
}
"""

    async def execute(self, text_analysis: Dict, vision_analysis: Optional[Dict] = None, audio_analysis: Optional[Dict] = None, ai_mode: str = "auto", raw_text: str = "") -> Dict[str, Any]:
        try:
            # Import agents inside to avoid circular dependencies
            from domain.agents.behaviour_agent import BehaviourAgent
            from domain.agents.knowledge_agent import KnowledgeAgent
            from domain.agents.timeline_agent import TimelineAgent
            from domain.agents.recommendation_agent import RecommendationAgent
            
            payload = {
                "text_agent_report": text_analysis,
                "vision_agent_report": vision_analysis,
                "audio_agent_report": audio_analysis
            }
            
            if raw_text:
                # Run the new intelligence agents in parallel
                b_task = asyncio.create_task(BehaviourAgent().execute({"text": raw_text, "ai_mode": ai_mode}, "temp"))
                k_task = asyncio.create_task(KnowledgeAgent().execute({"text": raw_text, "ai_mode": ai_mode}, "temp"))
                t_task = asyncio.create_task(TimelineAgent().execute({"text": raw_text, "ai_mode": ai_mode}, "temp"))
                r_task = asyncio.create_task(RecommendationAgent().execute({"text": raw_text, "ai_mode": ai_mode}, "temp"))
                
                results = await asyncio.gather(b_task, k_task, t_task, r_task, return_exceptions=True)
                
                payload["behaviour_analysis"] = results[0] if not isinstance(results[0], Exception) else {}
                payload["knowledge_analysis"] = results[1] if not isinstance(results[1], Exception) else {}
                payload["timeline_analysis"] = results[2] if not isinstance(results[2], Exception) else {}
                payload["recommendations"] = results[3] if not isinstance(results[3], Exception) else {}
            
            full_prompt = f"{self.system_prompt}\n\nINTELLIGENCE REPORTS:\n{json.dumps(payload, indent=2)}"
            
            result = await self.router.execute(prompt=full_prompt, context={}, ai_mode=ai_mode)
            
            result["models"] = ["fusion_orchestrator"]
            result["prompt_version"] = "v3.0_master_blueprint"
            return result
        except Exception as e:
            print(f"Fusion error: {e}")
            return {"error": f"Fusion failed: {str(e)}", "score": text_analysis.get("score", 0.0), "decision": "Fell back to text analysis."}
