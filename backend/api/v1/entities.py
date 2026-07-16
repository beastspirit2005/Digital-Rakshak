import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status

from infrastructure.repositories.entity_repository import EntityRepository
from domain.models.user import User
from api.deps import get_current_user_optional, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entities", tags=["National Threat Entity Intelligence"])


@router.get("/search")
async def search_threat_entities(
    query: str = Query("", description="Phone number, UPI domain, URL or IFSC to search"),
    entity_type: Optional[str] = Query(None, description="PHONE, UPI, URL, BANK_ACCOUNT"),
    limit: int = Query(50, ge=1, le=200),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search national cyber threat entity database by prefix, substring, or exact value.
    Returns linked cases, cross-jurisdictional risk scores, and attack campaign IDs.
    """
    repo = EntityRepository()
    results = await repo.search_entities(query=query, entity_type=entity_type, limit=limit)
    return {
        "count": len(results),
        "entities": results
    }


@router.get("/profile")
async def get_threat_entity_profile(
    value: str = Query(..., description="Exact entity value e.g. +91 98200 41029 or pay@hdfc.upi"),
    entity_type: str = Query("PHONE", description="PHONE, UPI, URL, BANK_ACCOUNT"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieves a 360-degree forensic profile for a specific threat entity.
    Queries Neo4j Attack DNA graph for linked cases across all jurisdictions.
    """
    repo = EntityRepository()
    profile = await repo.get_entity_profile(entity_type=entity_type, value=value)
    return profile


@router.post("/store", status_code=status.HTTP_201_CREATED)
async def store_threat_entity(
    case_number: str = Query(..., description="Associated case number"),
    entity_type: str = Query(..., description="PHONE, UPI, URL, BANK_ACCOUNT"),
    value: str = Query(..., description="Exact entity value"),
    risk_score: float = Query(0.85, description="Initial risk score 0.0 to 1.0"),
    admin: User = Depends(get_current_admin)
):
    """
    Manually register or update a threat entity in both graph and relational stores.
    """
    repo = EntityRepository()
    stored = await repo.store_entity(case_number=case_number, entity_type=entity_type, value=value, risk_score=risk_score)
    return stored
