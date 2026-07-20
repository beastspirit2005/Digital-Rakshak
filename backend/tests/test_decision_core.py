import pytest
from backend.shared.contexts.execution_state import ExecutionState
from backend.raic.decision.consensus import ConsensusEngine
from backend.raic.decision.calibration import ConfidenceCalibration
from backend.raic.decision.decision import DecisionEngine

def test_consensus_engine():
    state = ExecutionState(case_id="123", correlation_id="abc")
    state.ai_results = {
        "threat_agent": {"confidence": 0.8},
        "behaviour_agent": {"confidence": 0.85},
        "vision_agent": {"confidence": 0.82}
    }
    
    consensus = ConsensusEngine()
    result = consensus.determine_consensus(state)
    
    assert result["consensus_reached"] is True
    assert round(result["average_confidence"], 2) == 0.82
    assert result["variance"] < 0.05

def test_confidence_calibration():
    state = ExecutionState(case_id="123", correlation_id="abc")
    # P(A) = 0.5, P(B) = 0.5
    # Fused = 1 - (1-0.5)*(1-0.5) = 1 - 0.25 = 0.75
    state.ai_results = {
        "agent_a": {"confidence": 0.5},
        "agent_b": {"confidence": 0.5}
    }
    
    calibration = ConfidenceCalibration()
    fused_score = calibration.calibrate(state)
    
    assert fused_score == 0.75

def test_decision_engine():
    state = ExecutionState(case_id="123", correlation_id="abc")
    engine = DecisionEngine()
    
    state.confidence_score = 0.90
    decision = engine.make_decision(state)
    assert decision["decision"] == "TAKEDOWN_RECOMMENDED"
    
    state.confidence_score = 0.60
    decision = engine.make_decision(state)
    assert decision["decision"] == "MANUAL_REVIEW_REQUIRED"
    
    state.confidence_score = 0.30
    decision = engine.make_decision(state)
    assert decision["decision"] == "NO_ACTION"
