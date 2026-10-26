import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.db.session import Base

class OfficialLocation(Base):
    __tablename__ = "official_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Cyber Crime Police Station, CID Headquarters"
    jurisdiction_level = Column(String(50), default="district", nullable=False)  # state, district, central, zonal
    state = Column(String(100), nullable=False, index=True)  # e.g. "Karnataka"
    district = Column(String(100), nullable=False, index=True)  # e.g. "Bengaluru Urban"
    city = Column(String(100), nullable=True, index=True)  # e.g. "Bengaluru"
    pincode = Column(String(10), nullable=True, index=True)
    address = Column(Text, nullable=False)

    # Geographic coordinates (for Haversine radius math & map markers)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Official Contacts
    helpline_number = Column(String(50), nullable=True)  # e.g. "1930" or direct cell line
    landline_number = Column(String(50), nullable=True)
    official_email = Column(String(120), nullable=True)
    nodal_officer_designation = Column(String(120), nullable=True)

    # Authoritative Verification Metadata
    source_url = Column(String(500), nullable=False)  # e.g. "https://ksp.karnataka.gov.in"
    source_authority = Column(String(200), nullable=False)  # e.g. "Karnataka State Police"
    verification_status = Column(String(50), default="officially_listed", nullable=False)  # officially_listed | verified_coordinating_partner
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    review_due_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_official_locations_state_dist", "state", "district"),
        Index("idx_official_locations_lat_lng", "latitude", "longitude"),
    )
