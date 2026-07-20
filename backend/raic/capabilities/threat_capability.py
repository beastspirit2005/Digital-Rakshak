from typing import Any, Dict
from backend.shared.contracts.capability import ICapability
from backend.shared.contracts.engine import IEngine

class ThreatCapability(ICapability):
    """
    Decouples the Threat Agent from the underlying engine.
    Handles data validation and transformation.
    """
    def __init__(self, engine: IEngine):
        self._engine = engine

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError("ThreatCapability requires 'text' in payload.")
            
        # Execute the engine analysis
        engine_result = await self._engine.analyze({"text": text})
        
        # Standardize the output for the RAIC agent
        return engine_result
