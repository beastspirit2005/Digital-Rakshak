from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.shared.contexts.investigation import InvestigationContext, EvidenceContext

class IRepository(ABC):
    """Base generic interface for all repositories."""
    pass

class IEvidenceRepository(IRepository):
    @abstractmethod
    async def save_evidence(self, case_id: str, evidence: EvidenceContext) -> None:
        pass
        
    @abstractmethod
    async def get_evidence(self, case_id: str) -> List[EvidenceContext]:
        pass

class IInvestigationRepository(IRepository):
    @abstractmethod
    async def save_investigation(self, context: InvestigationContext) -> None:
        pass
        
    @abstractmethod
    async def get_investigation(self, case_id: str) -> Optional[InvestigationContext]:
        pass

class ICampaignRepository(IRepository):
    """Interacts with Vector/Graph database to track threat actor campaigns."""
    @abstractmethod
    async def find_similar_campaigns(self, embeddings: List[float], threshold: float = 0.8) -> List[Dict[str, Any]]:
        pass
        
    @abstractmethod
    async def link_evidence_to_campaign(self, evidence_id: str, campaign_id: str) -> None:
        pass
