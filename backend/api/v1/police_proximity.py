"""
Police & Investigator Proximity Spatial API
==========================================
Provides localized victim and case geographic intelligence for authorized
police officers and cyber cell investigators within a jurisdictional radius.

Enforces:
1. Role-Based Access Control: police, cyber_cell, admin.
2. Differential Privacy: ~300m jitter applied for unassigned cases.
3. Audit Event Logging: Every spatial query logged for compliance.
"""

import math
import uuid
import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from infrastructure.db.session import get_db
from api.deps import get_current_user
from domain.models.user import User
from domain.models.case import Case
from domain.models.audit_event import AuditEvent

router = APIRouter(prefix="/police", tags=["police-proximity"])

OFFICER_ROLES = {"police", "cyber_cell", "admin"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def apply_privacy_jitter(lat: float, lng: float, seed_str: str) -> tuple[float, float]:
    """
    Applies deterministic ~250m-300m differential privacy jitter
    so the exact street residence is not revealed before case assignment.
    """
    # Deterministic pseudo-randomness based on seed string
    seed = sum(ord(c) for c in str(seed_str))
    rng = random.Random(seed)
    # 0.0025 degrees is ~275 meters
    jitter_lat = lat + rng.uniform(-0.0025, 0.0025)
    jitter_lng = lng + rng.uniform(-0.0025, 0.0025)
    return round(jitter_lat, 6), round(jitter_lng, 6)


@router.get("/nearby-victims")
async def get_nearby_victims(
    request: Request,
    lat: float = Query(12.9818, ge=-90.0, le=90.0, description="Station or officer latitude"),
    lng: float = Query(77.5898, ge=-180.0, le=180.0, description="Station or officer longitude"),
    radius_km: float = Query(50.0, ge=1.0, le=200.0, description="Proximity search radius in km"),
    urgency: Optional[str] = Query(None, description="critical, high, standard, all"),
    is_ongoing_only: bool = Query(False, description="Filter for live ongoing fraud only"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns localized victim assistance requests within the specified radius.
    Restricted to authorized police and cyber cell investigators.
    """
    if user.role not in OFFICER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Authorized law enforcement or cyber cell personnel only."
        )

    # Fetch active cases
    query = select(Case)
    filters = []

    if urgency and urgency.lower() != "all":
        filters.append(Case.urgency_level == urgency.lower())

    if is_ongoing_only:
        filters.append(Case.is_ongoing_fraud == True)

    if filters:
        query = query.where(and_(*filters))

    res = await db.execute(query)
    cases = res.scalars().all()

    features: List[Dict[str, Any]] = []

    for c in cases:
        # Use case coordinates or fallback to city default
        c_lat = c.latitude
        c_lng = c.longitude

        if c_lat is None or c_lng is None:
            # Fallback to general Bengaluru/Delhi defaults if coordinates weren't set on submit
            c_lat = 12.9716 + (random.uniform(-0.05, 0.05))
            c_lng = 77.5946 + (random.uniform(-0.05, 0.05))

        dist = haversine_km(lat, lng, c_lat, c_lng)
        if dist > radius_km:
            continue

        is_assigned_to_me = (getattr(c, "assigned_to", None) == user.id)

        # Apply ~300m differential privacy jitter unless assigned to current officer
        if not is_assigned_to_me and user.role != "admin":
            disp_lat, disp_lng = apply_privacy_jitter(c_lat, c_lng, str(c.id))
            is_exact = False
        else:
            disp_lat, disp_lng = c_lat, c_lng
            is_exact = True

        ref = c.assistance_reference or c.case_number or str(c.id)[:8]
        urgency_val = getattr(c, "urgency_level", "standard") or "standard"

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [disp_lng, disp_lat]
            },
            "properties": {
                "case_id": str(c.id),
                "case_number": c.case_number,
                "reference": ref,
                "incident_type": c.scam_type_code or "Cyber Incident",
                "urgency_level": urgency_val,
                "is_ongoing_fraud": getattr(c, "is_ongoing_fraud", False),
                "estimated_loss_inr": getattr(c, "estimated_loss_inr", 0.0) or 0.0,
                "distance_km": dist,
                "city": c.city or "Unknown",
                "state": c.state or "Unknown",
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "narrative": (c.scam_text[:140] + "...") if c.scam_text and len(c.scam_text) > 140 else (c.scam_text or "No statement provided"),
                "is_assigned_to_me": is_assigned_to_me,
                "is_exact_location": is_exact,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        })

    # Sort features: Critical first, then by nearest distance
    urgency_weight = {"critical": 0, "high": 1, "standard": 2}
    features.sort(key=lambda f: (
        urgency_weight.get(f["properties"]["urgency_level"], 3),
        f["properties"]["distance_km"]
    ))

    # Log immutable audit event
    audit = AuditEvent(
        id=uuid.uuid4(),
        actor_id=user.id,
        actor_role=user.role,
        action="POLICE_PROXIMITY_SEARCH",
        resource_type="proximity_map",
        resource_id=f"lat={lat},lng={lng},r={radius_km}",
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={
            "radius_km": radius_km,
            "results_count": len(features),
            "urgency_filter": urgency
        }
    )
    db.add(audit)
    await db.commit()

    return {
        "type": "FeatureCollection",
        "station_anchor": {
            "latitude": lat,
            "longitude": lng,
        },
        "radius_km": radius_km,
        "total_count": len(features),
        "critical_count": sum(1 for f in features if f["properties"]["urgency_level"] == "critical"),
        "live_fraud_count": sum(1 for f in features if f["properties"]["is_ongoing_fraud"]),
        "features": features
    }
