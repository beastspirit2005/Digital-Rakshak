from typing import Dict, Any, List
from domain.models.transaction import FrictionAction, RiskBand


class AdaptiveFrictionEngine:
    """
    Decides the optimal fraud prevention action to minimize customer friction 
    while neutralizing risk.
    
    5 Outcomes:
    1. APPROVE (Zero friction, instant execution)
    2. APPROVE_AND_MONITOR (Low risk, background audit log)
    3. STEP_UP_VERIFICATION (Medium-high risk: OTP / biometric challenge, NOT blocked)
    4. TEMPORARY_HOLD (High risk: 15-minute freeze, citizen push notification)
    5. HOLD_AND_INVESTIGATE (Critical risk: immediate block + fraud investigation case)
    """

    def decide(
        self,
        risk_score: float,
        confidence: float,
        risk_band: str,
        features: Dict[str, float],
        sub_scores: Dict[str, float],
        attack_dna: float = 0.0,
        graph_risk: float = 0.0
    ) -> Dict[str, Any]:
        """
        Determines the proportional friction decision and deterministic reason codes.
        """
        reason_codes: List[str] = []

        # ------------------------------------------------------------------
        # 1. Deterministic Reason Code Extraction
        # ------------------------------------------------------------------
        if features.get("is_new_device", 0.0) == 1.0:
            reason_codes.append("NEW_DEVICE")
        
        if features.get("is_new_beneficiary", 0.0) == 1.0:
            reason_codes.append("NEW_BENEFICIARY")
            
        if features.get("velocity_anomaly_score", 0.0) >= 0.50 or features.get("txns_last_5m", 0.0) >= 4:
            reason_codes.append("VELOCITY_SPIKE")
            
        if features.get("amount_anomaly_score", 0.0) >= 0.60 or features.get("amount_ratio_to_avg", 0.0) >= 5.0:
            reason_codes.append("AMOUNT_ANOMALY")
            
        if features.get("is_unusual_hour", 0.0) == 1.0:
            reason_codes.append("SUSPICIOUS_HOURS")
            
        if features.get("location_anomaly_score", 0.0) >= 0.50:
            reason_codes.append("LOCATION_DEVIATION")
            
        if features.get("device_account_count", 1.0) >= 3.0:
            reason_codes.append("SHARED_DEVICE_RING")
            
        if features.get("beneficiary_risk_score", 0.0) >= 0.75:
            reason_codes.append("MULE_BENEFICIARY")
            
        if attack_dna >= 0.75:
            reason_codes.append("ATTACK_DNA_MATCH")
            
        if graph_risk >= 0.75:
            reason_codes.append("GRAPH_FRAUD_RING")

        if not reason_codes and risk_score < 0.20:
            reason_codes.append("NORMAL_PROFILE")

        # ------------------------------------------------------------------
        # 2. Adaptive Friction Decision Matrix
        # ------------------------------------------------------------------
        # If confidence is lower (< 0.70), we prefer STEP_UP over outright HOLD to avoid false positives!
        if risk_band == RiskBand.CRITICAL.value or risk_score >= 0.88:
            action = FrictionAction.HOLD_AND_INVESTIGATE.value
        elif risk_band == RiskBand.HIGH.value or risk_score >= 0.70:
            if confidence < 0.70 and "SHARED_DEVICE_RING" not in reason_codes and "ATTACK_DNA_MATCH" not in reason_codes:
                # Moderate confidence high risk: Step-up verification instead of cold block
                action = FrictionAction.STEP_UP_VERIFICATION.value
            else:
                action = FrictionAction.TEMPORARY_HOLD.value
        elif risk_band == RiskBand.ELEVATED.value or risk_score >= 0.45:
            action = FrictionAction.STEP_UP_VERIFICATION.value
        elif risk_band == RiskBand.GUARDED.value or risk_score >= 0.20:
            action = FrictionAction.APPROVE_AND_MONITOR.value
        else:
            action = FrictionAction.APPROVE.value

        # ------------------------------------------------------------------
        # 3. Deterministic Explanation Synthesis
        # ------------------------------------------------------------------
        explanation = self._build_deterministic_explanation(action, risk_score, confidence, reason_codes, features)

        return {
            "decision": action,
            "reason_codes": reason_codes,
            "explanation": explanation,
            "risk_score": risk_score,
            "confidence": confidence,
            "risk_band": risk_band
        }

    def _build_deterministic_explanation(
        self,
        action: str,
        risk_score: float,
        confidence: float,
        reason_codes: List[str],
        features: Dict[str, float]
    ) -> str:
        """Generates a truthful, hallucination-free explanation string."""
        pct = int(risk_score * 100)
        conf_pct = int(confidence * 100)
        
        if action == FrictionAction.APPROVE.value:
            return f"Transaction risk is low ({pct}%). Beneficiary and device match typical usage patterns with {conf_pct}% confidence."

        reasons_readable = []
        if "NEW_DEVICE" in reason_codes:
            reasons_readable.append("unrecognized device")
        if "NEW_BENEFICIARY" in reason_codes:
            reasons_readable.append("first-time beneficiary")
        if "VELOCITY_SPIKE" in reason_codes:
            txns = int(features.get("txns_last_5m", 0))
            reasons_readable.append(f"rapid velocity burst ({txns} txns in 5 min)")
        if "AMOUNT_ANOMALY" in reason_codes:
            amt = int(features.get("amount", 0))
            reasons_readable.append(f"unusual transfer volume (₹{amt:,})")
        if "SUSPICIOUS_HOURS" in reason_codes:
            reasons_readable.append("unusual early-morning transaction hours (01:00-05:00 AM)")
        if "SHARED_DEVICE_RING" in reason_codes:
            dev_cnt = int(features.get("device_account_count", 0))
            reasons_readable.append(f"device associated with {dev_cnt} distinct bank accounts")
        if "MULE_BENEFICIARY" in reason_codes:
            reasons_readable.append("beneficiary flagged in mule intelligence registry")
        if "ATTACK_DNA_MATCH" in reason_codes:
            reasons_readable.append("matches known Account Takeover sequence pattern")
        if "GRAPH_FRAUD_RING" in reason_codes:
            reasons_readable.append("connected to multi-account fraud syndicate in graph")

        reasons_str = "; ".join(reasons_readable) if reasons_readable else "deviations from historical profile"
        
        if action == FrictionAction.STEP_UP_VERIFICATION.value:
            return f"Flagged for Step-up Verification (Risk: {pct}%, Confidence: {conf_pct}%). Triggered by: {reasons_str}. Proceeding with biometric/OTP challenge rather than blocking customer."
        elif action == FrictionAction.TEMPORARY_HOLD.value:
            return f"Placed on Temporary 15-Minute Hold (Risk: {pct}%, Confidence: {conf_pct}%). Critical flags: {reasons_str}. Alert dispatched to citizen mobile app for authorization."
        elif action == FrictionAction.HOLD_AND_INVESTIGATE.value:
            return f"Transaction Held for Investigation (Risk: {pct}%, Confidence: {conf_pct}%). Severe signals detected: {reasons_str}. Automatic cyber cell case initiated."
        else:
            return f"Approved with Background Monitoring (Risk: {pct}%, Confidence: {conf_pct}%). Minor variations detected: {reasons_str}."

