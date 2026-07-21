from typing import Dict, Any
from shared.contexts.execution_state import ExecutionState

class DecisionEngine:
    """
    Renders the final policy/takedown decision based on consensus and calibration.
    """
    def make_decision(self, state: ExecutionState) -> Dict[str, Any]:
        if state.confidence_score > 0.85:
            decision = "TAKEDOWN_RECOMMENDED"
            action = "Escalate to Takedown API"
        elif state.confidence_score > 0.50:
            decision = "MANUAL_REVIEW_REQUIRED"
            action = "Flag for Human Analyst"
        else:
            decision = "NO_ACTION"
            action = "Close Case"
            
        return {
            "decision": decision,
            "action": action,
            "confidence_threshold": state.confidence_score
        }
