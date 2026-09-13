import pytest
from transaction.scoring_engine import TransactionScoringEngine
from transaction.friction_engine import AdaptiveFrictionEngine
from domain.models.transaction import FrictionAction, RiskBand


def test_scoring_and_friction_normal_approve():
    scoring = TransactionScoringEngine()
    friction = AdaptiveFrictionEngine()

    features = {
        "amount": 800.0,
        "amount_anomaly_score": 0.05,
        "velocity_anomaly_score": 0.0,
        "is_new_device": 0.0,
        "device_risk_score": 0.0,
        "is_new_beneficiary": 0.0,
        "beneficiary_risk_score": 0.0,
        "is_unusual_hour": 0.0,
        "location_anomaly_score": 0.0,
        "txns_last_24h": 5.0
    }

    scored = scoring.score_transaction(features, behaviour_score=0.05, graph_risk=0.0, campaign_score=0.0)
    assert scored["risk_score"] < 0.20
    assert scored["risk_band"] == RiskBand.LOW.value
    assert scored["confidence"] >= 0.85

    decision = friction.decide(
        risk_score=scored["risk_score"],
        confidence=scored["confidence"],
        risk_band=scored["risk_band"],
        features=features,
        sub_scores=scored["sub_scores"]
    )

    assert decision["decision"] == FrictionAction.APPROVE.value
    assert "NORMAL_PROFILE" in decision["reason_codes"]
    assert "low" in decision["explanation"].lower()


def test_scoring_and_friction_elevated_step_up():
    scoring = TransactionScoringEngine()
    friction = AdaptiveFrictionEngine()

    # Moderate anomaly: new beneficiary, large amount, normal device and daytime
    features = {
        "amount": 45000.0,
        "amount_anomaly_score": 0.75,
        "velocity_anomaly_score": 0.10,
        "is_new_device": 0.0,
        "device_risk_score": 0.0,
        "is_new_beneficiary": 1.0,
        "beneficiary_risk_score": 0.30,
        "is_unusual_hour": 0.0,
        "location_anomaly_score": 0.10,
        "txns_last_24h": 2.0
    }

    scored = scoring.score_transaction(features, behaviour_score=0.40, graph_risk=0.0, campaign_score=0.0)
    assert 0.20 <= scored["risk_score"] <= 0.70

    decision = friction.decide(
        risk_score=scored["risk_score"],
        confidence=scored["confidence"],
        risk_band=scored["risk_band"],
        features=features,
        sub_scores=scored["sub_scores"]
    )

    # Must be Step-up or Monitor, NEVER outright hold/block for moderate anomaly
    assert decision["decision"] in [FrictionAction.STEP_UP_VERIFICATION.value, FrictionAction.APPROVE_AND_MONITOR.value]
    assert "NEW_BENEFICIARY" in decision["reason_codes"]


def test_scoring_and_friction_critical_hold():
    scoring = TransactionScoringEngine()
    friction = AdaptiveFrictionEngine()

    # Severe Account Takeover: new device, rapid burst, new mule beneficiary at 2 AM, graph ring match
    features = {
        "amount": 95000.0,
        "amount_anomaly_score": 0.95,
        "velocity_anomaly_score": 0.90,
        "is_new_device": 1.0,
        "device_risk_score": 0.85,
        "device_account_count": 4.0,
        "is_new_beneficiary": 1.0,
        "new_beneficiary_high_risk": 1.0,
        "beneficiary_risk_score": 0.90,
        "is_unusual_hour": 1.0,
        "location_anomaly_score": 0.80,
        "txns_last_5m": 5.0,
        "txns_last_24h": 10.0
    }

    scored = scoring.score_transaction(
        features,
        behaviour_score=0.90,
        graph_risk=0.85,
        campaign_score=0.80
    )

    assert scored["risk_score"] >= 0.88
    assert scored["risk_band"] == RiskBand.CRITICAL.value

    decision = friction.decide(
        risk_score=scored["risk_score"],
        confidence=scored["confidence"],
        risk_band=scored["risk_band"],
        features=features,
        sub_scores=scored["sub_scores"],
        attack_dna=0.92,
        graph_risk=0.85
    )

    assert decision["decision"] == FrictionAction.HOLD_AND_INVESTIGATE.value
    assert "NEW_DEVICE" in decision["reason_codes"]
    assert "SHARED_DEVICE_RING" in decision["reason_codes"]
    assert "ATTACK_DNA_MATCH" in decision["reason_codes"]
    assert "MULE_BENEFICIARY" in decision["reason_codes"]

