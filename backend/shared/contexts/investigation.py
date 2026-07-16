from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class EvidenceContext(BaseModel):
    evidence_id: str
    content_type: str
    raw_data: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RuntimeContext(BaseModel):
    priority: str = "normal"
    timeout_seconds: int = 30
    strict_mode: bool = False

class ExecutionContext(BaseModel):
    correlation_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    actor_id: str

class InvestigationMetadata(BaseModel):
    tags: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    current_status: str = "OPEN"

class InvestigationContext(BaseModel):
    """
    The root composition object for an active investigation.
    Instead of a God Object, it holds strictly scoped sub-contexts.
    """
    case_id: str
    execution: ExecutionContext
    evidence: List[EvidenceContext] = Field(default_factory=list)
    runtime: RuntimeContext = Field(default_factory=RuntimeContext)
    metadata: InvestigationMetadata = Field(default_factory=InvestigationMetadata)

class AgentContext(BaseModel):
    """
    Context passed explicitly to an agent execution instance.
    """
    investigation_id: str
    evidence_target: EvidenceContext
    runtime: RuntimeContext
