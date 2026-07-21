from typing import Dict, Any, List
from shared.contexts.execution_state import ExecutionState

class EvidenceFusion:
    """
    Merges evidence streams and AI results into a fused feature set.
    """
    def fuse(self, state: ExecutionState) -> Dict[str, Any]:
        # Merge individual AI results into a single view
        fused_features = {}
        for agent, result in state.ai_results.items():
            if isinstance(result, dict) and "confidence" in result:
                fused_features[f"{agent}_confidence"] = result["confidence"]
        return fused_features
