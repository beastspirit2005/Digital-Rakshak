from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class DomainEvent(BaseModel):
    event_id: str
    timestamp: datetime
    correlation_id: str

class InvestigationStarted(DomainEvent):
    case_id: str
    triggered_by: str

class EvidenceUploaded(DomainEvent):
    case_id: str
    evidence_id: str
    evidence_type: str

class ThreatAnalysisCompleted(DomainEvent):
    case_id: str
    agent_id: str
    confidence: float
    threat_class: str
