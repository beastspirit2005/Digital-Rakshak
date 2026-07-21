from typing import Dict, Any, List
from shared.contexts.execution_state import ExecutionState

class ConsensusEngine:
    """
    Determines consensus between various AI agents.
    For example, do the vision, voice, and text agents agree?
    """
    def determine_consensus(self, state: ExecutionState) -> Dict[str, Any]:
        confidences = []
        for res in state.ai_results.values():
            if isinstance(res, dict) and "confidence" in res:
                confidences.append(res["confidence"])
        
        if not confidences:
            return {"consensus_reached": False, "average_confidence": 0.0}
            
        avg = sum(confidences) / len(confidences)
        variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
        
        # High consensus if variance is low
        consensus_reached = variance < 0.05
        
        return {
            "consensus_reached": consensus_reached,
            "average_confidence": avg,
            "variance": variance
        }
