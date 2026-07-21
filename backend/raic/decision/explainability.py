from typing import Dict, Any, List
from shared.contexts.execution_state import ExecutionState

class ExplainabilityEngine:
    """
    Builds human-readable and auditable decision reasons.
    """
    def generate_explanation(self, state: ExecutionState, decision_data: Dict[str, Any]) -> str:
        decision = decision_data.get("decision", "UNKNOWN")
        confidence = decision_data.get("confidence_threshold", 0.0)
        
        explanation = (
            f"Decision: {decision} reached with {confidence*100:.1f}% confidence. "
        )
        
        reasons = []
        for agent, res in state.ai_results.items():
            if isinstance(res, dict) and "threat_class" in res:
                reasons.append(f"{agent} detected {res['threat_class']}")
            elif isinstance(res, dict) and "behaviour_flags" in res:
                reasons.append(f"{agent} flagged: {', '.join(res['behaviour_flags'])}")
                
        if reasons:
            explanation += "Factors: " + "; ".join(reasons)
            
        return explanation
