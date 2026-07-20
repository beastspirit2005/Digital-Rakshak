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

class TimelineEvent(BaseModel):
    timestamp: datetime
    description: str
    source: str

class Entity(BaseModel):
    entity_id: str
    entity_type: str
    value: str

class InvestigationMetadata(BaseModel):
    source_system: str = "MANUAL"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InvestigationContext(BaseModel):
    """
    The immutable root composition object for an active investigation.
    Represents the facts of the case that do not change during execution.
    """
    case_id: str
    evidence: List[EvidenceContext] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    metadata: InvestigationMetadata = Field(default_factory=InvestigationMetadata)

class AgentContext(BaseModel):
    """
    Context passed explicitly to an agent execution instance.
    Combines the immutable investigation facts with the current execution state.
    """
    investigation_id: str
    correlation_id: str
    evidence_target: Optional[EvidenceContext] = None
    runtime: RuntimeContext

