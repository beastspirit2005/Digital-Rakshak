from abc import ABC, abstractmethod
from typing import Any, Dict

class IRuntime(ABC):
    """
    Base contract for all RIE Runtimes.
    Runtimes handle hardware execution, model loading, and health checks.
    """
    
    @abstractmethod
    async def infer(self, payload: Any) -> Any:
        pass
        
    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass

class IThreatRuntime(IRuntime):
    pass

class IVisionRuntime(IRuntime):
    pass

class IVoiceRuntime(IRuntime):
    pass

class IBehaviourRuntime(IRuntime):
    pass

class IEmbeddingRuntime(IRuntime):
    pass

class INERRuntime(IRuntime):
    pass

class IReasoningRuntime(IRuntime):
    pass
