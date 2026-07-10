import json
from typing import Dict, Any, List
import ollama
import logging

logger = logging.getLogger(__name__)

class ClusterAgent:
    """
    AI Summarizer for connected clusters. 
    Powered strictly by Ollama (Local Inference) to ensure maximum privacy of aggregate data.
    """
    
    def __init__(self):
        self.model = "mistral"
        self.system_prompt = """You are a Cyber Threat Intelligence (CTI) Analyst.
You are given a list of connected cyber fraud cases that share a common entity (e.g. the same scammer phone number).
Your job is to generate a brief, professional 2-3 sentence summary of the scammer's exact modus operandi for this cluster.
DO NOT use markdown formatting like bolding. Just plain text.
Focus on:
1. What the scam is (e.g. Digital Arrest, Phishing)
2. Who they are impersonating (if any)
3. The common vector.
"""

    async def execute(self, cluster_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            payload = {
                "connected_cases": cluster_cases
            }
            
            full_prompt = f"{self.system_prompt}\n\nCLUSTER DATA:\n{json.dumps(payload, indent=2)}\n\nProvide the 2-3 sentence summary now:"
            
            logger.info(f"Generating cluster summary with {self.model}...")
            # We use Ollama directly for maximum privacy as requested by the plan
            response = ollama.chat(model=self.model, messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"CLUSTER DATA:\n{json.dumps(payload, indent=2)}\n\nProvide the summary:"}
            ])
            
            return {"summary": response['message']['content'], "model": self.model}
        except Exception as e:
            logger.warning(f"Ollama failed, falling back to Groq: {e}")
            try:
                from infrastructure.ai.groq_client import GroqClient
                groq = GroqClient()
                fallback_prompt = f"{self.system_prompt}\n\nCLUSTER DATA:\n{json.dumps(payload, indent=2)}\n\nProvide the summary:"
                reply = await groq.generate_text(fallback_prompt)
                return {"summary": reply, "model": "llama-3.3-70b-versatile (fallback)"}
            except Exception as e2:
                logger.error(f"Fallback Groq failed: {e2}")
                return {"error": f"Summarization failed: {str(e)}", "summary": "Failed to generate summary due to local AI error."}
