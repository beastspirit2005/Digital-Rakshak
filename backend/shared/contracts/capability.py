from abc import ABC, abstractmethod
from typing import Any

class ICapability(ABC):
    """
    Capabilities decouple RAIC Agents from RIE Runtimes.
    They handle the routing, formatting, and validation of data before sending it to a Runtime.
    """
    
    @abstractmethod
    async def invoke(self, payload: Any) -> Any:
        """
        Invoke the capability. Returns a standardized RuntimeResult.
        """
        pass
