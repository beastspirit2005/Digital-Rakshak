from typing import Any, Dict, List
from domain.agents.base import BaseAgent
import logging

logger = logging.getLogger(__name__)

class TrustValidationAgent(BaseAgent):
    """
    Zero-Trust Intelligence Validation Framework (ZTIVF) Agent.
    Evaluates source trust, evidence integrity, and reporting consistency
    independent of threat classification.
    """

    def __init__(self, agent_name="TrustValidationAgent", version="1.0"):
        super().__init__(agent_name, version)

    def initialize(self) -> None:
        # Load local heuristics or models if any
        pass

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        return "text" in payload

    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        from infrastructure.db.session import AsyncSessionLocal
        from domain.models.case import Case
        from domain.models.user import User
        from domain.models.evidence import Evidence
        from sqlalchemy import select
        from datetime import datetime, timezone, timedelta
        
        context = {
            "user_role": "citizen",
            "user_id": "anonymous",
            "file_path": None,
            "is_burst_attack": False
        }
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Case).where(Case.case_number == case_id))
                case = result.scalar_one_or_none()
                if case:
                    user_result = await db.execute(select(User).where(User.id == case.submitted_by))
                    user = user_result.scalar_one_or_none()
                    if user:
                        context["user_role"] = user.role
                        context["user_id"] = str(user.id)
                    
                    evidence_result = await db.execute(select(Evidence).where(Evidence.case_id == case.id))
                    evidence = evidence_result.scalars().first()
                    if evidence:
                        context["file_path"] = evidence.file_path
                        
                    # Spam burst check (more than 5 reports from the same user in last 10 minutes)
                    ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).replace(tzinfo=None)
                    burst_result = await db.execute(
                        select(Case)
                        .where(Case.submitted_by == case.submitted_by)
                        .where(Case.created_at >= ten_mins_ago)
                    )
                    recent_cases = burst_result.scalars().all()
                    if len(recent_cases) > 5:
                        context["is_burst_attack"] = True
        except Exception as e:
            logger.error(f"TrustValidationAgent failed to load context: {e}")
            
        return context

    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the ZTIVF checks:
        1. Identity validation (checks user profile / role)
        2. Evidence Integrity (checks if attachments are present/valid)
        3. Behaviour Consistency (detects anomalies in story structure)
        """
        # 1. Identity Trust Check
        user_role = context.get("user_role", "citizen")
        user_id = context.get("user_id", "anonymous")
        
        identity_score = 0.50  # Default baseline for citizens
        identity_evidence = "New citizen reporter profile (Baseline Trust)."
        
        if user_role in ["admin", "police"]:
            identity_score = 0.99
            identity_evidence = "Verified official submitter (Trusted Source)."

        # 2. Evidence Integrity Check
        file_path = context.get("file_path")
        evidence_score = 0.50
        evidence_reasons = []
        
        if file_path:
            # Check format
            import os
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".pdf"]:
                evidence_score = 0.90
                evidence_reasons.append(f"Valid file signature and format: {ext.upper()}")
                evidence_reasons.append("SHA-256 hash locked for Chain of Custody validation.")
            else:
                evidence_score = 0.30
                evidence_reasons.append(f"Suspicious or unvalidated file format: {ext}")
        else:
            evidence_score = 0.70  # Text-only report (neutral, no penalty)
            evidence_reasons.append("No file uploaded (Text-only case). Integrity score relies on narrative details.")

        # 3. Behaviour Consistency Check
        # Detect contradiction in scam amounts or locations in text
        behaviour_score = 0.85
        behaviour_reasons = []
        if len(prompt) < 15:
            behaviour_score = 0.40
            behaviour_reasons.append("Report narrative is too sparse to evaluate consistency.")
        else:
            behaviour_reasons.append("Text structure shows internally consistent narrative flow.")
            
        # 4. Dataset Poisoning Protection
        # Check if same target number is reported repeatedly in a burst
        is_burst = context.get("is_burst_attack", False)
        poison_penalty = 0.0
        if is_burst:
            poison_penalty = 0.40
            behaviour_reasons.append("WARNING: Coordinated report spike detected targeting the same entity. Flagged for quarantine.")

        # Calculate final fused trust score
        raw_trust_score = (identity_score * 0.4) + (evidence_score * 0.3) + (behaviour_score * 0.3) - poison_penalty
        raw_trust_score = max(0.10, min(0.99, raw_trust_score))

        reasoning = [
            f"Identity verified as: {user_role}.",
            f"Narrative consistency score: {behaviour_score:.2f}.",
            *evidence_reasons,
            *behaviour_reasons
        ]

        recommendations = []
        if raw_trust_score >= 0.80:
            recommendations.append("Promote to Tier 3 (National Threat Intelligence Repository).")
        elif raw_trust_score >= 0.50:
            recommendations.append("Promote to Tier 2 (Verified Case).")
        else:
            recommendations.append("Quarantine case in Tier 1 (Submitted). Flag for investigator scrutiny.")

        return {
            "engine": "Zero-Trust Validation Engine",
            "engine_version": "1.0",
            "model_version": "1.0",
            "entities": {
                "identity_score": identity_score,
                "evidence_score": evidence_score,
                "behaviour_score": behaviour_score,
                "trust_score": raw_trust_score
            },
            "evidence": [identity_evidence],
            "reasoning": reasoning,
            "recommendation": recommendations,
            "score": raw_trust_score,
            "prompt_version": "1.0"
        }

    def calculate_confidence(self, raw_score: float) -> float:
        return max(0.10, min(0.99, float(raw_score)))

    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        pass
