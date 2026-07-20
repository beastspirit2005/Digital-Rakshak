from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ExecutionState(BaseModel):
    """
    Mutable state representing the continuous progress of an investigation's execution.
    Contains AI results, decisions, campaign intelligence, and recommendations.
    """
    case_id: str
    correlation_id: str
    status: str = "INITIALIZED"
    confidence_score: float = 0.0
    
    # Intelligence Results
    ai_results: Dict[str, Any] = Field(default_factory=dict)
    campaign_intelligence: Dict[str, Any] = Field(default_factory=dict)
    
    # Workflow State
    current_stage: str = "PENDING"
    completed_stages: List[str] = Field(default_factory=list)
    graph_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Decisions & Recommendations
    decision: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)
    
    # Logging / Traceability
    errors: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_status(self, new_status: str):
        self.status = new_status
        self.last_updated_at = datetime.utcnow()
        
    def add_error(self, error_msg: str):
        self.errors.append(error_msg)
        self.last_updated_at = datetime.utcnow()
