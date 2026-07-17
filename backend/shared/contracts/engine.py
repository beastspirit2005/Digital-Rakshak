from abc import ABC, abstractmethod
from typing import Any, Dict

class IEngine(ABC):
    """
    Contract for Domain Engines.
    Engines contain business intelligence and orchestrate one or more runtimes.
    """
    
    @abstractmethod
    async def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute domain-specific analysis.
        
        Args:
            payload: Input data required by the engine.
            
        Returns:
            Dict containing the engine's intelligence findings.
        """
        pass

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Name of the engine."""
        pass
