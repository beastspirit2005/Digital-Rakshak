from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class DomainEvent(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str
    case_id: str

class InvestigationCreated(DomainEvent):
    triggered_by: str

class EvidenceValidated(DomainEvent):
    evidence_id: str
    is_valid: bool

class EvidenceStored(DomainEvent):
    evidence_id: str
    storage_path: str

class ThreatCompleted(DomainEvent):
    agent_id: str
    confidence: float
    threat_class: str

class BehaviourCompleted(DomainEvent):
    agent_id: str
    confidence: float
    behaviour_flags: list[str]

class CampaignCompleted(DomainEvent):
    agent_id: str
    confidence: float
    campaign_name: str

class ConsensusCompleted(DomainEvent):
    fused_confidence: float

class DecisionGenerated(DomainEvent):
    decision_type: str
    reasoning: str

class RecommendationGenerated(DomainEvent):
    recommendation_text: str

class InvestigationClosed(DomainEvent):
    final_status: str
