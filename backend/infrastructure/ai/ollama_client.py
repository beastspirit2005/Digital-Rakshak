import json
import logging
from typing import Dict, Any, Optional
import ollama
from core.config import settings

logger = logging.getLogger(__name__)

LEGACY_MODEL_MAP = {
    "mistral": "llama3:8b",
    "qwen2.5:7b": "llama3:8b",
    "qwen2.5": "llama3:8b",
    "mistral:7b": "llama3:8b",
    "llama3": "llama3:8b"
}

SYSTEM_CYBER_INTEL_PROMPT = """You are an elite Indian Cyber Threat Intelligence and Fraud Prevention AI.
Your objective is to analyze whether the provided payload (SMS, message, URL, UPI ID, or phone number) is a FRAUD/SCAM/CYBER THREAT or a SAFE/LEGITIMATE communication.

GROUND TRUTH RULES FOR ACCURATE EVALUATION:
1. LEGITIMATE BANK ALERTS: Standard bank transaction SMS ("debited from a/c", "credited to a/c", balance alerts, genuine OTPs with "Do not share OTP", official bank shortcodes like 56767, official toll-free numbers) are SAFE. They inform the user of account activity and do NOT demand clicking suspicious external links or transferring funds.
2. PHISHING / KYC SCAMS: Messages threatening account suspension/deactivation within 24 hours, demanding clicking on third-party links (e.g., sbi-kyc.com, pan-update.in), or asking to call private mobile numbers (+91-9xxx) to prevent account block are SCAMS (threat_type: Banking Fraud).
3. DIGITAL ARREST / POLICE THREATS: Claims of parcel with drugs/passports intercepted at customs, fake CBI/Mumbai Police arrest threats, Skype/video call interrogation demands are SCAMS (threat_type: Digital Arrest).
4. ELECTRICITY BILL DISCONNECTION: Urgent threats of power disconnect at 9:30 PM tonight demanding calling personal phone numbers are SCAMS (threat_type: Utility Scam).
5. PART-TIME JOB / TASK SCAM: Offers of earning Rs 2000-5000 daily by liking YouTube videos, Google Maps reviews, Telegram tasks are SCAMS (threat_type: Task Scam).
6. UPI / REFUND FRAUDS: Asking user to click link to 'claim' money, enter UPI PIN to receive refund, or fake accidental transfer stories are SCAMS (threat_type: UPI Fraud).
7. LEGITIMATE SERVICES: Official Google, Microsoft, Amazon, Swiggy, Zomato, IRCTC, or Govt (.gov.in) domains and notifications are SAFE.
8. E-COMMERCE DELIVERY PINS VS COURIER SCAMS: In Indian e-commerce (Amazon, Flipkart, Swiggy, Zomato), delivery alerts often say "out for delivery with associate...", "share delivery PIN only upon package arrival", or order tracking. These are normal, legitimate delivery handoffs and are SAFE (threat_type: None). Courier SCAMS, by contrast, demand advance clearance fees or customs duty, claim contraband/passports/narcotics found in packages, or demand money transfer.

OUTPUT FORMAT:
You MUST respond with ONLY a valid raw JSON object matching this schema:
{
  "is_scam": boolean,
  "decision": "Safe" | "Suspicious" | "Critical",
  "threat_type": "None" | "Banking Fraud" | "UPI Fraud" | "Digital Arrest" | "Courier Scam" | "Utility Scam" | "Task Scam" | "Malware / APK",
  "confidence": float between 0.50 and 1.00,
  "score": float between 0.50 and 1.00,
  "reason": "Clear concise explanation of why this payload is safe or a scam",
  "evidence": [{"relevance": "string"}]
}
"""

class OllamaClient:
    """
    Client for Local Ollama inference.
    Used for offline privacy-sensitive scanning, zero-day threat reasoning, and fallback intelligence.
    """
    
    def __init__(self):
        self.default_model = getattr(settings, "OLLAMA_MODEL", "llama3:8b")
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)

    def _resolve_model(self, model_name: Optional[str] = None) -> str:
        if not model_name:
            return self.default_model
        return LEGACY_MODEL_MAP.get(model_name, model_name)

    async def analyze(self, prompt: str, context: Optional[Dict[str, Any]] = None, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a prompt and optional context to local Ollama with structured JSON output.
        """
        model = self._resolve_model(model_name)
        context_data = context or {}

        # Prepare messages with system grounding and structured prompt
        user_message_content = f"{prompt}\nContext: {json.dumps(context_data)}" if context_data else prompt

        try:
            response = await self.client.chat(
                model=model,
                messages=[
                    {'role': 'system', 'content': SYSTEM_CYBER_INTEL_PROMPT},
                    {'role': 'user', 'content': user_message_content}
                ],
                format='json',
                options={
                    'temperature': 0.1  # Low temperature for highly consistent, deterministic threat classification
                }
            )
            
            if not hasattr(response, 'message') or not hasattr(response.message, 'content') or not response.message.content:
                raise ValueError(f"Unexpected Ollama response structure: {response}")
                
            raw_content = response.message.content.strip()
            result = json.loads(raw_content)
            
            # Normalize and enforce schema consistency
            is_scam = result.get("is_scam")
            decision = str(result.get("decision", "")).strip()
            
            # If is_scam is not boolean, infer from decision or threat_type
            if is_scam is None:
                if any(w in decision.lower() for w in ["critical", "malicious", "scam", "threat", "phishing", "fraud"]):
                    is_scam = True
                elif any(w in decision.lower() for w in ["safe", "clean", "legitimate", "benign"]):
                    is_scam = False
                else:
                    is_scam = False

            conf = float(result.get("confidence", result.get("score", 0.85)))
            
            result["is_scam"] = is_scam
            result["score"] = conf
            result["confidence"] = conf
            if "decision" not in result or not result["decision"]:
                result["decision"] = "Critical" if is_scam else "Safe"
            if "threat_type" not in result:
                result["threat_type"] = "Scam / Cyber Threat" if is_scam else "None"
            if "reason" not in result:
                result["reason"] = "Evaluated by offline intelligence model."
            if "evidence" not in result:
                result["evidence"] = []
                
            result["models"] = [f"ollama-{model}"]
            result["prompt_version"] = "v2.0-cyber-grounded"
            return result
            
        except Exception as e:
            logger.warning("Ollama API Error: %s", e)
            return {
                "is_scam": False,
                "decision": f"Ollama Inference Error: {str(e)}",
                "threat_type": "None",
                "score": 0.0,
                "confidence": 0.0,
                "reason": f"Offline AI inference encountered an error: {str(e)}",
                "evidence": [],
                "models": [f"ollama-{model}"],
                "prompt_version": "v2.0-fallback"
            }

    async def generate_text(self, prompt: str, model_name: Optional[str] = None) -> str:
        """
        Sends a raw prompt to Ollama for a conversational or unstructured text response.
        """
        model = self._resolve_model(model_name)
        try:
            response = await self.client.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.3}
            )
            if not hasattr(response, 'message') or not hasattr(response.message, 'content') or not response.message.content:
                return "Ollama Inference Error: Unexpected API response structure."
            return response.message.content
        except Exception as e:
            logger.warning("Ollama API Error (generate_text): %s", e)
            return f"Ollama Inference Error: {str(e)}"
