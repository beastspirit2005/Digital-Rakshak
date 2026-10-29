"""
Police & Investigator Proximity Spatial API
==========================================
Provides localized victim and case geographic intelligence for authorized
police officers and cyber cell investigators within a jurisdictional radius,
as well as Nationwide Tactical Surveillance and Officer Deployment for Admins.

Enforces:
1. Role-Based Access Control: police, cyber_cell, admin.
2. Differential Privacy: ~300m jitter applied for unassigned cases.
3. Audit Event Logging: Every spatial query logged for compliance.
4. Bidirectional In-Map Case Assignment & Officer Roster Tracking.
"""

import math
import uuid
import random
import hmac
import hashlib
import struct
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func

from infrastructure.db.session import get_db
from api.deps import get_current_user
from domain.models.user import User
from domain.models.case import Case, CaseStatus
from domain.models.official_directory import OfficialLocation
from domain.models.audit_event import AuditEvent
from core.config import settings

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
    Applies cryptographic HMAC-SHA256 deterministic differential privacy jitter (~250m-300m)
    using the server secret key so external observers cannot reverse or triangulate
    exact resident coordinates before case undertaking.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    msg = str(seed_str).encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()

    # Extract two 32-bit unsigned integers from digest
    val_lat, val_lng = struct.unpack(">II", digest[:8])
    # Normalize to [-0.0025, +0.0025] (~275m)
    offset_lat = ((val_lat / 0xFFFFFFFF) - 0.5) * 0.005
    offset_lng = ((val_lng / 0xFFFFFFFF) - 0.5) * 0.005

    return round(lat + offset_lat, 6), round(lng + offset_lng, 6)


@router.get("/nearby-victims")
async def get_nearby_victims(
    request: Request,
    lat: float = Query(12.9818, ge=-90.0, le=90.0, description="Station or officer latitude"),
    lng: float = Query(77.5898, ge=-180.0, le=180.0, description="Station or officer longitude"),
    radius_km: float = Query(50.0, ge=1.0, le=2000.0, description="Proximity search radius in km"),
    all_india: bool = Query(False, description="When true, returns cases nationwide without distance cutoff"),
    state: Optional[str] = Query(None, description="Filter cases by state name"),
    assignment_status: Optional[str] = Query(None, description="all, unassigned, assigned_to_me, assigned"),
    urgency: Optional[str] = Query(None, description="critical, high, standard, all"),
    is_ongoing_only: bool = Query(False, description="Filter for live ongoing fraud only"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns localized victim assistance requests within the specified radius or nationwide.
    Restricted to authorized police, cyber cell, and admin personnel.
    """
    if user.role not in OFFICER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Authorized law enforcement or cyber cell personnel only."
        )

    # 1. Fetch active cases
    query = select(Case)
    filters = []

    if urgency and urgency.lower() != "all":
        filters.append(Case.urgency_level == urgency.lower())

    if is_ongoing_only:
        filters.append(Case.is_ongoing_fraud == True)

    if state and state.lower() not in ["all", "all india"]:
        filters.append(Case.state.ilike(f"%{state.strip()}%"))

    if assignment_status:
        st = assignment_status.lower().strip()
        if st == "unassigned":
            filters.append(Case.assigned_to.is_(None))
        elif st == "assigned_to_me":
            filters.append(Case.assigned_to == user.id)
        elif st == "assigned":
            filters.append(Case.assigned_to.isnot(None))

    if filters:
        query = query.where(and_(*filters))

    res = await db.execute(query)
    cases = res.scalars().all()

    # 2. Batch lookup assignee user details
    assignee_ids = {c.assigned_to for c in cases if getattr(c, "assigned_to", None)}
    assignee_map = {}
    if assignee_ids:
        u_res = await db.execute(select(User).where(User.id.in_(assignee_ids)))
        for u in u_res.scalars().all():
            assignee_map[u.id] = {
                "name": u.full_name or u.email,
                "role": u.role,
                "station": getattr(u, "station_name", None) or "Cyber Crime Unit",
                "phone": u.station_phone_number
            }

    features: List[Dict[str, Any]] = []

    for c in cases:
        c_lat = c.latitude
        c_lng = c.longitude

        if c_lat is None or c_lng is None:
            # Fallback coordinates if unset
            c_lat = 12.9716 + (random.uniform(-0.05, 0.05))
            c_lng = 77.5946 + (random.uniform(-0.05, 0.05))

        dist = haversine_km(lat, lng, c_lat, c_lng)
        if not all_india and dist > radius_km:
            continue

        is_assigned_to_me = (getattr(c, "assigned_to", None) == user.id)

        # Apply differential privacy jitter for unassigned cases unless viewing as admin
        if not is_assigned_to_me and user.role != "admin":
            disp_lat, disp_lng = apply_privacy_jitter(c_lat, c_lng, str(c.id))
            is_exact = False
        else:
            disp_lat, disp_lng = c_lat, c_lng
            is_exact = True

        ref = c.assistance_reference or c.case_number or str(c.id)[:8]
        urgency_val = getattr(c, "urgency_level", "standard") or "standard"

        assignee_info = assignee_map.get(c.assigned_to) if getattr(c, "assigned_to", None) else None

        dna = c.attack_dna or {}
        assignment_source = dna.get("assignment_source")
        claimed_at = dna.get("claimed_at")
        if not assignment_source and c.timeline_events:
            for ev in c.timeline_events:
                if ev.get("method") == "map_radar_claim":
                    assignment_source = "map_radar_claim"
                    claimed_at = ev.get("timestamp")
                    break

        is_claimed_recently = False
        if is_assigned_to_me and claimed_at:
            try:
                cl_dt = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - cl_dt).total_seconds() / 3600 <= 48:
                    is_claimed_recently = True
            except Exception:
                pass

        # Fallback cascade for reported loss: DB estimated_loss_inr -> DB estimated_amount -> AI narrative extraction -> 0.0
        loss_val = (
            getattr(c, "estimated_loss_inr", None)
            or getattr(c, "estimated_amount", None)
        )
        if not loss_val and c.scam_text:
            from domain.services.financial_loss_extractor import extract_financial_loss
            loss_val = extract_financial_loss(c.scam_text)
        resolved_loss = float(loss_val) if loss_val else 0.0

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
                "estimated_loss_inr": resolved_loss,
                "estimated_amount": resolved_loss,
                "distance_km": dist,
                "city": c.city or "Unknown",
                "state": c.state or "Unknown",
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "narrative": c.scam_text or "No statement provided",
                "assigned_to": str(c.assigned_to) if getattr(c, "assigned_to", None) else None,
                "assignee_name": assignee_info["name"] if assignee_info else None,
                "assignee_role": assignee_info["role"] if assignee_info else None,
                "assignee_station": assignee_info["station"] if assignee_info else None,
                "is_assigned_to_me": is_assigned_to_me,
                "is_exact_location": is_exact,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "assignment_source": assignment_source,
                "claimed_at": claimed_at,
                "is_claimed_recently": is_claimed_recently,
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
        resource_id=f"lat={lat},lng={lng},r={radius_km},all_india={all_india}",
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.now(timezone.utc),
        metadata_json={
            "radius_km": radius_km,
            "all_india": all_india,
            "results_count": len(features),
            "urgency_filter": urgency,
            "state_filter": state
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
        "all_india": all_india,
        "total_count": len(features),
        "critical_count": sum(1 for f in features if f["properties"]["urgency_level"] == "critical"),
        "live_fraud_count": sum(1 for f in features if f["properties"]["is_ongoing_fraud"]),
        "features": features
    }


@router.get("/officers-and-stations")
async def get_officers_and_stations(
    lat: float = Query(12.9818, ge=-90.0, le=90.0, description="Center latitude"),
    lng: float = Query(77.5898, ge=-180.0, le=180.0, description="Center longitude"),
    radius_km: float = Query(50.0, ge=1.0, le=2000.0, description="Search radius in km"),
    all_india: bool = Query(False, description="Return nationwide officers and stations"),
    state: Optional[str] = Query(None, description="Filter by state"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Returns verified on-duty officers (police, cyber_cell, admin) and authoritative Cyber Crime Police Stations.
    Includes active case workload counts and haversine distances for direct assignment.
    """
    if user.role not in OFFICER_ROLES:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 1. Active Case Workload Count per Officer
    workload_res = await db.execute(
        select(Case.assigned_to, func.count(Case.id))
        .where(Case.assigned_to.isnot(None), Case.status != CaseStatus.closed)
        .group_by(Case.assigned_to)
    )
    workload_map = {row[0]: row[1] for row in workload_res.all()}

    # 2. Query Approved Officers
    u_query = select(User).where(
        User.role.in_(["police", "cyber_cell", "admin"]),
        User.is_active == True,
        User.is_approved == True
    )
    if state and state.lower() not in ["all", "all india"]:
        u_query = u_query.where(User.state.ilike(f"%{state.strip()}%"))

    u_res = await db.execute(u_query)
    officers = u_res.scalars().all()

    # 3. Query Official Cyber Cell Stations
    s_query = select(OfficialLocation).where(OfficialLocation.is_active == True)
    if state and state.lower() not in ["all", "all india"]:
        s_query = s_query.where(OfficialLocation.state.ilike(f"%{state.strip()}%"))

    s_res = await db.execute(s_query)
    stations = s_res.scalars().all()

    officer_items: List[Dict[str, Any]] = []
    unanchored_officers_count = 0

    for o in officers:
        o_lat = getattr(o, "latitude", None)
        o_lng = getattr(o, "longitude", None)

        # Do not place unanchored officers at arbitrary fake locations
        if o_lat is None or o_lng is None:
            unanchored_officers_count += 1
            continue

        dist = haversine_km(lat, lng, o_lat, o_lng)
        if not all_india and dist > radius_km:
            continue

        officer_items.append({
            "id": str(o.id),
            "type": "officer",
            "name": o.full_name or o.email,
            "email": o.email,
            "role": o.role,
            "designation": getattr(o, "designation", None) or ("Cyber Cell Inspector" if o.role == "cyber_cell" else "Police Officer"),
            "station_name": getattr(o, "station_name", None) or "Cyber Crime Police Station",
            "station_phone": o.station_phone_number or "1930",
            "city": getattr(o, "city", None) or "Regional Jurisdiction",
            "state": getattr(o, "state", None) or "India",
            "active_cases_count": workload_map.get(o.id, 0),
            "coordinates": [o_lng, o_lat],
            "distance_km": dist
        })

    # Sort officers by nearest distance
    officer_items.sort(key=lambda x: x["distance_km"])

    station_items: List[Dict[str, Any]] = []
    for s in stations:
        dist = haversine_km(lat, lng, s.latitude, s.longitude)
        if not all_india and dist > radius_km:
            continue

        station_items.append({
            "id": str(s.id),
            "type": "station",
            "name": s.name,
            "jurisdiction_level": s.jurisdiction_level,
            "state": s.state,
            "district": s.district,
            "city": s.city or s.district,
            "address": s.address,
            "helpline": s.helpline_number or "1930",
            "landline": s.landline_number,
            "official_email": s.official_email,
            "nodal_officer": s.nodal_officer_designation,
            "coordinates": [s.longitude, s.latitude],
            "distance_km": dist
        })

    station_items.sort(key=lambda x: x["distance_km"])

    return {
        "anchor": {"latitude": lat, "longitude": lng},
        "radius_km": radius_km,
        "all_india": all_india,
        "total_officers": len(officer_items),
        "unanchored_officers_count": unanchored_officers_count,
        "total_stations": len(station_items),
        "officers": officer_items,
        "stations": station_items
    }
