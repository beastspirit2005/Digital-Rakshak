import json
import logging
import time
from typing import Any, Dict, List, Optional
from domain.agents.base import BaseAgent
from transaction.feature_engine import FeatureEngine
from transaction.attack_dna import AttackDNAMatcher
from transaction.scoring_engine import TransactionScoringEngine
from transaction.friction_engine import AdaptiveFrictionEngine
from core.config import settings

logger = logging.getLogger(__name__)


class TransactionAgent(BaseAgent):
    """
    RAIC Transaction Intelligence Agent.
    Converts raw financial transactions and historical context into deterministic 
    fraud signals, attack DNA matches, and adaptive friction recommendations.
    """

    def __init__(self, agent_name="TransactionAgent", version="1.0"):
        super().__init__(agent_name, version)

    def initialize(self) -> None:
        self.feature_engine = FeatureEngine()
        self.attack_dna_matcher = AttackDNAMatcher()
        self.scoring_engine = TransactionScoringEngine()
        self.friction_engine = AdaptiveFrictionEngine()

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        # Minimum required fields
        return "amount" in payload and "account_id" in payload and "beneficiary_id" in payload

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        """
        Retrieves graph risk intelligence and past transactions from Neo4j / DB if available.
        """
        return {}

    async def analyze_transaction(
        self,
        current_txn: Dict[str, Any],
        account_history: Optional[List[Dict[str, Any]]] = None,
        beneficiary_profile: Optional[Dict[str, Any]] = None,
        device_profile: Optional[Dict[str, Any]] = None,
        user_baseline: Optional[Dict[str, Any]] = None,
        graph_risk_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Full end-to-end evaluation pipeline for a transaction.
        """
        start_time = time.time()
        txn_id = current_txn.get("transaction_id", f"TXN-{int(start_time * 1000)}")

        # 1. Compute Deterministic Statistical Features
        features = self.feature_engine.compute_features(
            current_txn=current_txn,
            account_history=account_history,
            beneficiary_profile=beneficiary_profile,
            device_profile=device_profile,
            user_baseline=user_baseline
        )

        # 2. Sequence Match against Attack DNA templates
        dna_match = self.attack_dna_matcher.evaluate(
            current_txn=current_txn,
            features=features,
            account_history=account_history
        )
        dna_score = float(dna_match.get("similarity", 0.0)) if dna_match.get("matched") else 0.0

        # 3. Query Neo4j Graph for Fraud Ring Connections (if graph available and not overridden)
        graph_risk = graph_risk_override if graph_risk_override is not None else 0.0
        ring_details = {}
        if graph_risk_override is None:
            try:
                from infrastructure.graph.neo4j_client import IntelligenceGraph
                graph = IntelligenceGraph()
                ring_res = await graph.get_transaction_fraud_ring(
                    account_id=current_txn.get("account_id"),
                    beneficiary_id=current_txn.get("beneficiary_id"),
                    device_id=current_txn.get("device_id")
                )
                graph_risk = max(graph_risk, float(ring_res.get("graph_risk_score", 0.0)))
                ring_details = ring_res
            except Exception as e:
                logger.warning(f"Neo4j graph ring check skipped: {e}")

        # 4. Composite Scoring
        scored = self.scoring_engine.score_transaction(
            features=features,
            behaviour_score=features.get("is_unusual_hour", 0.0) * 0.5,
            graph_risk=graph_risk,
            campaign_score=dna_score
        )

        # 5. Friction Decision & Reason Codes
        decision_res = self.friction_engine.decide(
            risk_score=scored["risk_score"],
            confidence=scored["confidence"],
            risk_band=scored["risk_band"],
            features=features,
            sub_scores=scored["sub_scores"],
            attack_dna=dna_score,
            graph_risk=graph_risk
        )

        # 6. Format Standard Signals Array (as per RAIC specification)
        signals = [
            {"name": "amount_anomaly", "score": scored["sub_scores"]["amount"]},
            {"name": "velocity_anomaly", "score": scored["sub_scores"]["velocity"]},
            {"name": "new_beneficiary", "score": scored["sub_scores"]["beneficiary"]},
            {"name": "device_risk", "score": scored["sub_scores"]["device"]},
            {"name": "behaviour_deviation", "score": scored["sub_scores"]["behaviour"]},
            {"name": "graph_risk", "score": scored["sub_scores"]["graph"]},
            {"name": "attack_dna", "score": round(dna_score, 4)}
        ]

        # 7. Dual-Mode LLM Narrative Synthesis (Optional natural language enrichment)
        explanation = decision_res["explanation"]
        if decision_res["risk_score"] >= 0.45:
            polished = await self._generate_llm_explanation(current_txn, decision_res["reason_codes"], explanation)
            if polished:
                explanation = polished

        inference_time_ms = int((time.time() - start_time) * 1000)

        return {
            "transaction_id": txn_id,
            "signals": signals,
            "risk_score": scored["risk_score"],
            "confidence": scored["confidence"],
            "risk_band": scored["risk_band"],
            "decision": decision_res["decision"],
            "reason_codes": decision_res["reason_codes"],
            "explanation": explanation,
            "sub_scores": scored["sub_scores"],
            "features": features,
            "attack_dna": dna_match,
            "graph_risk": ring_details,
            "inference_time_ms": inference_time_ms
        }

    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implements BaseAgent inference interface."""
        return await self.analyze_transaction(context.get("transaction", {}))

    def calculate_confidence(self, raw_score: float) -> float:
        return min(0.99, max(0.50, raw_score))

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        """Publishes outcome to event bus / redis if available."""
        pass

    async def _generate_llm_explanation(
        self,
        current_txn: Dict[str, Any],
        reason_codes: List[str],
        base_explanation: str
    ) -> Optional[str]:
        """
        Uses Dual-Mode AI (Ollama offline / Groq online) to produce fluent investigator narratives.
        Falls back seamlessly to base deterministic explanation on any error.
        """
        prompt = (
            f"You are a Banking Fraud Prevention Copilot. In 2 concise sentences, summarize this decision for an investigator.\n"
            f"Transaction: Amount ₹{current_txn.get('amount')}, Channel: {current_txn.get('channel', 'UPI')}.\n"
            f"Facts/Reason Codes: {', '.join(reason_codes)}.\n"
            f"Core Analysis: {base_explanation}\n"
            f"Answer professionally without speculation."
        )

        ai_mode = settings.DEFAULT_AI_MODE
        if settings.FORCE_LOCAL_INFERENCE:
            ai_mode = "ollama"

        try:
            if ai_mode == "groq":
                try:
                    from infrastructure.ai.groq_client import GroqClient
                    res = await GroqClient().analyze(prompt, {"system": "You are a fraud investigator assistant."})
                    if res and res.get("decision"):
                        return res["decision"].strip()
                except Exception as groq_err:
                    logger.warning(f"Groq explanation failed, falling back to Ollama: {groq_err}")
                    ai_mode = "ollama"

            if ai_mode == "ollama":
                from infrastructure.ai.ollama_client import OllamaClient
                res = await OllamaClient().generate_text(prompt, model_name="llama3:8b")
                if res:
                    return res.strip()
        except Exception as e:
            logger.debug(f"LLM explanation enrichment skipped: {e}")

        return None

    async def enrich_explanation(
        self,
        current_txn: Dict[str, Any],
        reason_codes: List[str],
        base_explanation: str
    ) -> Optional[str]:
        """
        Public method to generate or enrich natural language investigator narrative.
        """
        try:
            polished = await self._generate_llm_explanation(current_txn, reason_codes, base_explanation)
            if polished:
                return polished
        except Exception as e:
            logger.warning(f"enrich_explanation LLM error: {e}")

        if reason_codes:
            return f"Transaction flagged with reason codes [{', '.join(reason_codes)}]. {base_explanation}"
        return base_explanation

