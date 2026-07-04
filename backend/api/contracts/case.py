from pydantic import BaseModel, Field
from typing import List, Optional

class CaseSubmissionRequest(BaseModel):
    scam_text: str = Field(..., max_length=5000, description="The raw text/description of the scam")
    city: Optional[str] = None
    state: Optional[str] = None
    estimated_amount: Optional[float] = None
    priority: str = "medium"

class CaseResponse(BaseModel):
    case_number: str
    status: str
    threat_confidence_score: Optional[float] = None
    scam_type_code: Optional[str] = None
