from abc import ABC, abstractmethod
from typing import Any, Dict

class IAgent(ABC):
    """
    Base contract for all RAIC Agents.
    Agents orchestrate capabilities but do not execute inference directly.
    """
    
    @abstractmethod
    async def execute(self, context: Any) -> Any:
        """
        Execute the agent logic based on the provided AgentContext.
        Returns an AgentResult.
        """
        pass
