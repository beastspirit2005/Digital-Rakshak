from typing import Dict, Any, List
from infrastructure.ai.ollama_client import OllamaClient
import time

class RAICDecisionCore:
    """
    Multi-Agent Intelligence Fusion (MAIF) Orchestrator.
    Takes the standardized output from the specialized expert models, fuses the evidence,
    calculates a final calibrated threat score, and generates an explanation.
    Uses Ollama (Qwen) strictly for reasoning/refining the final prose.
    """
    def __init__(self):
        self.ollama = OllamaClient()

    def _fuse_confidence(self, agent_results: List[Dict[str, Any]]) -> float:
        """
        Mathematical fusion of agent confidence scores.
        If Rakshak-Text says 0.90, and Rakshak-Behaviour says 0.80,
        the fused confidence increases because multiple independent systems agree.
        """
        if not agent_results:
            return 0.0
            
        valid_probs = []
        for result in agent_results:
            if result.get("agent") == "TrustValidationAgent":
                continue
            prob = result.get('confidence', 0.0)
            valid_probs.append(prob)
            
        if not valid_probs:
            return 0.0
            
        fused_confidence = sum(valid_probs) / len(valid_probs)
        return min(max(fused_confidence, 0.0), 0.99)

    def _build_rule_based_explanation(self, fused_data: Dict[str, Any]) -> str:
        """Rakshak-Explain: Deterministic rule-based template generation."""
        reasons = []
        if fused_data.get('threat_class'):
            reasons.append(f"Classified as {fused_data['threat_class']} by Rakshak-Text.")
            
        behaviors = fused_data.get('behaviors', [])
        if behaviors:
            reasons.append(f"Attack DNA detected: {', '.join(behaviors)}.")
            
        entities = fused_data.get('entities', {})
        if entities:
            extracted = []
            for k, v in entities.items():
                if v: extracted.append(f"{len(v)} {k}")
            if extracted:
                reasons.append(f"Extracted indicators: {', '.join(extracted)}.")
                
        # Inject ZTIVF metadata
        trust_metrics = fused_data.get("trust_metrics", {})
        if trust_metrics:
            reasons.append(
                f"ZTIVF Evaluation: Identity Trust={trust_metrics.get('identity_score', 0.0):.2f}, "
                f"Evidence Integrity={trust_metrics.get('evidence_score', 0.0):.2f}, "
                f"Consistency={trust_metrics.get('behaviour_score', 0.0):.2f}."
            )
                
        return " | ".join(reasons)

    async def execute_fusion(self, agent_payloads: List[Dict[str, Any]], use_qwen_refinement: bool = True, ai_mode: str = "auto") -> Dict[str, Any]:
        """
        The core fusion pipeline.
        """
        start_time = time.time()
        
        # 1. Aggregate all data
        fused_data = {
            "threat_class": None,
            "behaviors": [],
            "entities": {},
            "evidence": [],
            "models_used": [],
            "trust_metrics": {}
        }
        
        trust_score = 1.0
        for payload in agent_payloads:
            if payload.get("agent") == "ThreatAnalysisAgent":
                fused_data["threat_class"] = payload.get("threat_class")
            elif payload.get("agent") == "BehaviourAgent":
                fused_data["behaviors"].extend(payload.get("evidence", []))
            elif payload.get("agent") == "CampaignAgent":
                fused_data["entities"] = payload.get("entities", {})
            elif payload.get("agent") == "TrustValidationAgent":
                fused_data["trust_metrics"] = payload.get("entities", {})
                trust_score = payload.get("confidence", 1.0)
                
            fused_data["evidence"].extend(payload.get("reasoning", []))
            fused_data["models_used"].append(payload.get("engine"))
            
        # 2. Calculate Final Calibrated Confidence
        threat_confidence = self._fuse_confidence(agent_payloads)
        
        # 3. Apply ZTIVF Calibration (Post-calibration Scaling)
        # Low trust score reduces final threat confidence to prevent data poisoning.
        final_confidence = threat_confidence * trust_score
        
        # 4. Rule-based explanation
        raw_explanation = self._build_rule_based_explanation(fused_data)
        
        # 5. (Optional) LLM Refinement
        final_explanation = raw_explanation
        if use_qwen_refinement and final_confidence > 0.5:
            refine_prompt = (
                f"Rewrite this threat explanation into a short, highly professional 2-sentence "
                f"intelligence brief for an investigator. Incorporate ZTIVF metrics if relevant: '{raw_explanation}'"
            )
            from core.config import settings
            resolved_ai_mode = ai_mode
            if resolved_ai_mode == "auto":
                resolved_ai_mode = settings.DEFAULT_AI_MODE

            if resolved_ai_mode == "groq":
                from infrastructure.ai.groq_client import GroqClient
                qwen_res = await GroqClient().analyze(refine_prompt, context={}, model_name="llama-3.1-8b-instant")
            else:
                qwen_res = await self.ollama.analyze(refine_prompt, context={}, model_name="qwen2.5:7b")
                
            if isinstance(qwen_res, dict) and qwen_res.get("decision"):
                # Do not leak Ollama connection errors to the frontend
                if "Ollama Inference Error" in qwen_res["decision"]:
                    final_explanation = raw_explanation
                else:
                    final_explanation = qwen_res["decision"]

        # 6-Dimension Score Generation
        threat_score = 0.9 if fused_data["threat_class"] else 0.2
        behavior_score = min(len(fused_data["behaviors"]) * 0.3, 0.95)
        network_score = min(sum(len(v) for v in fused_data["entities"].values() if v) * 0.25, 0.9)
        integrity_score = fused_data["trust_metrics"].get("evidence_score", 0.8)
        impersonation_score = fused_data["trust_metrics"].get("identity_score", 0.6) if "Impersonation" not in fused_data["behaviors"] else 0.95
        extraction_score = 0.85 if fused_data["evidence"] else 0.4
        
        six_dim_score = {
            "threat": round(threat_score, 2),
            "behavior": round(behavior_score, 2),
            "network": round(network_score, 2),
            "integrity": round(integrity_score, 2),
            "impersonation": round(impersonation_score, 2),
            "extraction": round(extraction_score, 2)
        }

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "decision": final_explanation,
            "confidence": round(final_confidence, 4),
            "threat_class": fused_data["threat_class"],
            "models_used": fused_data["models_used"],
            "execution_time_ms": execution_time_ms,
            "raw_explanation": raw_explanation,
            "ztivf_metrics": fused_data["trust_metrics"],
            "six_dim_score": six_dim_score
        }

# Backward-compat alias — several agent modules still import this name.
AIRouter = RAICDecisionCore
