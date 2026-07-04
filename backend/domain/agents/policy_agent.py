import json
from typing import Dict, Any
from domain.agents.router import AIRouter

class PolicyAgent:
    """
    Automated Takedown Engine.
    Takes a confirmed scam AI decision and generates actionable JSON policies for banks and telecoms.
    """
    
    def __init__(self):
        self.router = AIRouter()
        self.system_prompt = """You are the Policy Enforcement Engine for the Digital Rakshak platform.
You will be provided with an AI threat analysis report that has confirmed a scam (Confidence > 0.85).
Your job is to extract the actionable entities (UPI IDs, bank accounts, phone numbers, URLs) and map them to takedown policies.
Generate a JSON output in the following format exactly:
{
  "policies": [
    {
      "target": "string (the entity, e.g. 9876543210 or scammer@upi)",
      "type": "string (phone, upi, bank, url)",
      "action": "string (block_imei, freeze_account, block_domain)",
      "reason": "string (brief justification based on the scam report)"
    }
  ]
}
If no actionable entities exist, return an empty list for policies.
"""

    async def execute(self, threat_report: Dict[str, Any], ai_mode: str = "auto") -> Dict[str, Any]:
        try:
            full_prompt = f"{self.system_prompt}\n\nTHREAT REPORT:\n{json.dumps(threat_report, indent=2)}"
            
            result = await self.router.execute(prompt=full_prompt, context={}, ai_mode=ai_mode)
            
            return result
        except Exception as e:
            return {"error": f"Policy generation failed: {str(e)}", "policies": []}
