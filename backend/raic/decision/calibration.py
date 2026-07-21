from typing import Dict, Any, List
from shared.contexts.execution_state import ExecutionState

class ConfidenceCalibration:
    """
    Calibrates confidence independently.
    Fuses probabilities using independent probability fusion or Bayesian updates.
    """
    def calibrate(self, state: ExecutionState) -> float:
        valid_probs = []
        for res in state.ai_results.values():
            if isinstance(res, dict) and "confidence" in res:
                valid_probs.append(res["confidence"])
                
        if not valid_probs:
            return 0.0
            
        # Independent probability fusion: P(A U B) = 1 - (1-P(A))(1-P(B))
        inv_prod = 1.0
        for p in valid_probs:
            inv_prod *= (1.0 - p)
            
        fused_confidence = 1.0 - inv_prod
        return min(max(fused_confidence, 0.0), 0.99)
