from typing import Dict, Any, Optional
from domain.models.transaction import RiskBand


DEFAULT_WEIGHTS = {
    "velocity": 0.20,
    "amount": 0.15,
    "device": 0.15,
    "beneficiary": 0.15,
    "behaviour": 0.15,
    "graph": 0.10,
    "campaign": 0.10,
}


class TransactionScoringEngine:
    """
    Combines feature signals, graph intelligence, behaviour baseline, and campaign matches
    into a single normalized risk score (0.0 - 1.0) and confidence score.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        # Normalize weights to sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def score_transaction(
        self,
        features: Dict[str, float],
        behaviour_score: float = 0.0,
        graph_risk: float = 0.0,
        campaign_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Computes composite risk score and confidence.
        
        :param features: Output from FeatureEngine
        :param behaviour_score: Deviation from historical baseline (0.0 to 1.0)
        :param graph_risk: Network/fraud ring connectivity score (0.0 to 1.0)
        :param campaign_score: Similarity to active fraud campaigns (0.0 to 1.0)
        :return: {risk_score, confidence, risk_band, sub_scores}
        """
        # 1. Normalize individual sub-signals to [0.0, 1.0]
        vel_signal = min(1.0, max(0.0, features.get("velocity_anomaly_score", 0.0)))
        amt_signal = min(1.0, max(0.0, features.get("amount_anomaly_score", 0.0)))
        dev_signal = min(1.0, max(0.0, features.get("device_risk_score", 0.0)))
        if features.get("is_new_device", 0.0) == 1.0:
            dev_signal = max(dev_signal, 0.40)

        ben_signal = min(1.0, max(0.0, features.get("beneficiary_risk_score", 0.0)))
        if features.get("new_beneficiary_high_risk", 0.0) == 1.0:
            ben_signal = max(ben_signal, 0.60)
        elif features.get("is_new_beneficiary", 0.0) == 1.0:
            ben_signal = max(ben_signal, 0.25)

        beh_signal = min(1.0, max(0.0, behaviour_score))
        if features.get("is_unusual_hour", 0.0) == 1.0:
            beh_signal = max(beh_signal, 0.50)

        gra_signal = min(1.0, max(0.0, graph_risk))
        cam_signal = min(1.0, max(0.0, campaign_score))

        sub_scores = {
            "velocity": round(vel_signal, 4),
            "amount": round(amt_signal, 4),
            "device": round(dev_signal, 4),
            "beneficiary": round(ben_signal, 4),
            "behaviour": round(beh_signal, 4),
            "graph": round(gra_signal, 4),
            "campaign": round(cam_signal, 4),
        }

        # 2. Weighted sum
        raw_risk = (
            sub_scores["velocity"] * self.weights.get("velocity", 0.20) +
            sub_scores["amount"] * self.weights.get("amount", 0.15) +
            sub_scores["device"] * self.weights.get("device", 0.15) +
            sub_scores["beneficiary"] * self.weights.get("beneficiary", 0.15) +
            sub_scores["behaviour"] * self.weights.get("behaviour", 0.15) +
            sub_scores["graph"] * self.weights.get("graph", 0.10) +
            sub_scores["campaign"] * self.weights.get("campaign", 0.10)
        )

        # Non-linear boost if multiple severe signals correlate (synergy)
        high_severity_count = sum(1 for s in sub_scores.values() if s >= 0.70)
        if high_severity_count >= 3:
            raw_risk = min(1.0, raw_risk * 1.30)
        elif high_severity_count >= 2:
            raw_risk = min(1.0, raw_risk * 1.15)

        risk_score = round(min(1.0, max(0.0, raw_risk)), 4)

        # 3. Calculate Confidence
        # Higher confidence if we have history (more past txns) and concordant signals
        past_txns = features.get("txns_last_24h", 0.0)
        base_conf = 0.75 if past_txns > 0 else 0.60
        # If signals strongly agree (either all low or multiple high), confidence increases
        if high_severity_count >= 2 or risk_score <= 0.15:
            base_conf += 0.20
        confidence = round(min(0.99, base_conf), 4)

        # 4. Assign Risk Band
        if risk_score < 0.20:
            band = RiskBand.LOW.value
        elif risk_score < 0.45:
            band = RiskBand.GUARDED.value
        elif risk_score < 0.70:
            band = RiskBand.ELEVATED.value
        elif risk_score < 0.88:
            band = RiskBand.HIGH.value
        else:
            band = RiskBand.CRITICAL.value

        return {
            "risk_score": risk_score,
            "confidence": confidence,
            "risk_band": band,
            "sub_scores": sub_scores,
        }

