from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class AgentResult(BaseModel):
    """
    Standardized return object from all RAIC Agents.
    The DecisionCore consumes this predictable structure without needing to special-case individual agents.
    """
    status: str  # e.g., 'SUCCESS', 'FAILED', 'INCONCLUSIVE'
    confidence: float
    execution_time_ms: int
    findings: List[str] = Field(default_factory=list)
    evidence_links: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
