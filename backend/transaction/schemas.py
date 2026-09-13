from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class TransactionCreate(BaseModel):
    transaction_id: Optional[str] = Field(None, description="Unique transaction ID. Generated if omitted.")
    account_id: str = Field(..., description="Source account identifier, e.g. ACC-10293")
    beneficiary_id: str = Field(..., description="Destination VPA or Account ID, e.g. user@okhdfc")
    device_id: Optional[str] = Field(None, description="Fingerprint of user device")
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    currency: str = Field("INR", description="Currency code")
    transaction_type: str = Field("UPI", description="Payment rail: UPI, IMPS, NEFT, CARD")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp (UTC)")
    latitude: Optional[float] = Field(None, description="Geographic latitude")
    longitude: Optional[float] = Field(None, description="Geographic longitude")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State name")
    channel: str = Field("MOBILE", description="Channel: MOBILE, WEB, ATM, POS")
    raw_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class TransactionRead(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    beneficiary_id: str
    device_id: Optional[str] = None
    amount: float
    currency: str
    transaction_type: str
    timestamp: datetime
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    channel: str
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    decision: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FeatureVector(BaseModel):
    transaction_id: str
    features: Dict[str, float]
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class RiskScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float
    confidence: float
    risk_band: str
    sub_scores: Dict[str, float]
    model_version: str = "v1.0"


class ExplanationResponse(BaseModel):
    transaction_id: str
    risk_score: float
    confidence: float
    decision: str
    reason_codes: List[str]
    explanation_text: str
    sub_scores: Dict[str, float]
    attack_dna_match: Optional[Dict[str, Any]] = None
    graph_risk: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    investigator_id: Optional[str] = Field(None, description="Investigator username/ID")
    human_decision: str = Field(..., description="CONFIRMED_FRAUD, FALSE_POSITIVE, or LEGITIMATE_ANOMALY")
    notes: Optional[str] = Field(None, description="Investigator review notes")


class RiskFeedItem(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    beneficiary_id: str
    amount: float
    transaction_type: str
    timestamp: datetime
    risk_score: float
    confidence: float
    risk_band: str
    decision: str
    top_reason_code: Optional[str] = None

