import uuid
import math
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.db.session import get_db
from api.deps import require_pro_user, get_current_admin
from domain.models.user import User
from domain.models.official_directory import OfficialLocation
from domain.models.audit_event import AuditEvent

router = APIRouter(prefix="/official-locations", tags=["official-locations"])

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

class LocationCreateRequest(BaseModel):
    name: str = Field(..., description="e.g. Cyber Crime Police Station, CID")
    jurisdiction_level: str = Field("district", description="state, district, central, zonal")
    state: str = Field(..., description="e.g. Karnataka")
    district: str = Field(..., description="e.g. Bengaluru Urban")
    city: Optional[str] = None
    pincode: Optional[str] = None
    address: str = Field(..., description="Full physical address")
    latitude: float
    longitude: float
    helpline_number: Optional[str] = "1930"
    landline_number: Optional[str] = None
    official_email: Optional[str] = None
    nodal_officer_designation: Optional[str] = None
    source_url: str = Field(..., description="Official government verification URL")
    source_authority: str = Field(..., description="e.g. State Police Portal")
    verification_status: str = Field("officially_listed", description="officially_listed or verified_coordinating_partner")

@router.get("")
async def search_official_locations(
    request: Request,
    state: Optional[str] = None,
    district: Optional[str] = None,
    pincode: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 50.0,
    db: AsyncSession = Depends(get_db),
    # Pro Guard: Free citizens receive HTTP 402; Official roles have complimentary access
    user: User = Depends(require_pro_user),
):
    """
    Search verified official cybercrime police stations.
    Premium Pro Feature: Requires active Digital Rakshak Pro subscription (or institutional role).
    """
    query = select(OfficialLocation).where(OfficialLocation.is_active == True)

    if state:
        query = query.where(OfficialLocation.state.ilike(f"%{state.strip()}%"))
    if district:
        query = query.where(OfficialLocation.district.ilike(f"%{district.strip()}%"))
    if pincode:
        query = query.where(OfficialLocation.pincode == pincode.strip())

    res = await db.execute(query)
    locations = res.scalars().all()

    results = []
    for loc in locations:
        distance = None
        if lat is not None and lng is not None:
            distance = haversine_km(lat, lng, loc.latitude, loc.longitude)
            if distance > radius_km:
                continue

        results.append({
            "id": str(loc.id),
            "name": loc.name,
            "jurisdiction_level": loc.jurisdiction_level,
            "state": loc.state,
            "district": loc.district,
            "city": loc.city,
            "pincode": loc.pincode,
            "address": loc.address,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "helpline_number": loc.helpline_number,
            "landline_number": loc.landline_number,
            "official_email": loc.official_email,
            "nodal_officer_designation": loc.nodal_officer_designation,
            "source_url": loc.source_url,
            "source_authority": loc.source_authority,
            "verification_status": loc.verification_status,
            "last_verified_at": loc.last_verified_at.isoformat() if loc.last_verified_at else None,
            "distance_km": distance
        })

    # Sort by distance if GPS query
    if lat is not None and lng is not None:
        results.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 999999)

    return {
        "locations": results,
        "count": len(results),
        "emergency_helpline": "1930",
        "official_reporting_portal": "https://cybercrime.gov.in/"
    }

@router.get("/{location_id}")
async def get_official_location_detail(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
):
    """
    Retrieves full verified location record and victim preparation checklist.
    """
    try:
        loc_uuid = uuid.UUID(location_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location UUID")

    res = await db.execute(select(OfficialLocation).where(OfficialLocation.id == loc_uuid))
    loc = res.scalars().first()
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    return {
        "id": str(loc.id),
        "name": loc.name,
        "jurisdiction_level": loc.jurisdiction_level,
        "state": loc.state,
        "district": loc.district,
        "city": loc.city,
        "pincode": loc.pincode,
        "address": loc.address,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "helpline_number": loc.helpline_number,
        "landline_number": loc.landline_number,
        "official_email": loc.official_email,
        "nodal_officer_designation": loc.nodal_officer_designation,
        "source_url": loc.source_url,
        "source_authority": loc.source_authority,
        "verification_status": loc.verification_status,
        "last_verified_at": loc.last_verified_at.isoformat() if loc.last_verified_at else None,
        "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={loc.latitude},{loc.longitude}",
        "what_to_bring": [
            "Bank statement showing the transaction UTR / Reference number",
            "Screenshots of fraudulent chats, SMS, or deceptive payment links",
            "Copy of Government ID (Aadhaar / Voter ID / Passport)",
            "Digital Rakshak Case Summary Reference (if created)",
            "Details of suspect's mobile number, UPI ID, or account number"
        ]
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_official_location(
    body: LocationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin-only: Add a verified official cybercrime police station to the directory.
    """
    loc_id = uuid.uuid4()
    new_loc = OfficialLocation(
        id=loc_id,
        name=body.name,
        jurisdiction_level=body.jurisdiction_level,
        state=body.state,
        district=body.district,
        city=body.city,
        pincode=body.pincode,
        address=body.address,
        latitude=body.latitude,
        longitude=body.longitude,
        helpline_number=body.helpline_number,
        landline_number=body.landline_number,
        official_email=body.official_email,
        nodal_officer_designation=body.nodal_officer_designation,
        source_url=body.source_url,
        source_authority=body.source_authority,
        verification_status=body.verification_status,
        last_verified_at=datetime.now(timezone.utc),
    )
    db.add(new_loc)

    # Audit log
    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="OFFICIAL_LOCATION_CREATED",
        resource_type="official_location",
        resource_id=str(loc_id),
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "name": body.name,
            "state": body.state,
            "source_url": body.source_url,
            "verification_status": body.verification_status
        }
    )
    db.add(audit)

    await db.commit()
    await db.refresh(new_loc)

    return {"status": "success", "id": str(loc_id), "name": new_loc.name}
