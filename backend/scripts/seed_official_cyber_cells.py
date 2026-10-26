"""
Seed initial authoritative Official Cyber Police Stations and Cyber Cells into official_locations.
Sources are verified state police official portals and Ministry of Home Affairs (MHA) directory.
"""
import sys
import os
import asyncio
import uuid
from datetime import datetime, timezone

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from infrastructure.db.session import AsyncSessionLocal
from domain.models.official_directory import OfficialLocation

SEEDED_STATIONS = [
    {
        "name": "Cyber Crime Police Station, CID Headquarters",
        "jurisdiction_level": "state",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "pincode": "560001",
        "address": "Carlton House, Palace Road, Bengaluru, Karnataka 560001",
        "latitude": 12.9818,
        "longitude": 77.5898,
        "helpline_number": "1930",
        "landline_number": "080-22094498",
        "official_email": "ccpscid@ksp.gov.in",
        "nodal_officer_designation": "Superintendent of Police, Cyber Crime Division, CID",
        "source_url": "https://ksp.karnataka.gov.in/page/Cyber+Crime/en",
        "source_authority": "Karnataka State Police / CID Karnataka",
        "verification_status": "officially_listed",
    },
    {
        "name": "IFSO (Intelligence Fusion & Strategic Operations), Special Cell",
        "jurisdiction_level": "state",
        "state": "Delhi",
        "district": "South West Delhi",
        "city": "New Delhi",
        "pincode": "110078",
        "address": "Sector 16-C, Dwarka, New Delhi 110078",
        "latitude": 28.5997,
        "longitude": 77.0326,
        "helpline_number": "1930",
        "landline_number": "011-20892633",
        "official_email": "ifso-specialcell@delhipolice.gov.in",
        "nodal_officer_designation": "DCP, IFSO Unit, Special Cell, Delhi Police",
        "source_url": "https://delhipolice.gov.in/cybercell",
        "source_authority": "Delhi Police, Ministry of Home Affairs",
        "verification_status": "officially_listed",
    },
    {
        "name": "Maharashtra State Cyber Police Headquarters",
        "jurisdiction_level": "state",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "city": "Mumbai",
        "pincode": "400005",
        "address": "32nd Floor, Centre-1, World Trade Centre, Cuffe Parade, Mumbai, Maharashtra 400005",
        "latitude": 18.9174,
        "longitude": 72.8184,
        "helpline_number": "1930",
        "landline_number": "022-22160080",
        "official_email": "mahacyber@mahapolice.gov.in",
        "nodal_officer_designation": "Special Inspector General of Police (Spl. IG), Cyber",
        "source_url": "https://cybercrime.gov.in / https://mahapolice.gov.in",
        "source_authority": "Maharashtra State Cyber Crime Branch",
        "verification_status": "officially_listed",
    },
    {
        "name": "TGCSB (Telangana Cyber Security Bureau) Headquarters",
        "jurisdiction_level": "state",
        "state": "Telangana",
        "district": "Hyderabad",
        "city": "Hyderabad",
        "pincode": "500004",
        "address": "DGP Office Complex, Saifabad, Lakdikapool, Hyderabad, Telangana 500004",
        "latitude": 17.4042,
        "longitude": 78.4682,
        "helpline_number": "1930",
        "landline_number": "040-27852448",
        "official_email": "sp-tgcsb@tspolice.gov.in",
        "nodal_officer_designation": "Superintendent of Police, TGCSB",
        "source_url": "https://tspolice.gov.in",
        "source_authority": "Telangana State Police",
        "verification_status": "officially_listed",
    },
    {
        "name": "State Cyber Crime Wing Headquarters, Tamil Nadu Police",
        "jurisdiction_level": "state",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "pincode": "600083",
        "address": "Police Telecommunication Complex, 2nd Floor, 100 Feet Road, Ashok Nagar, Chennai, Tamil Nadu 600083",
        "latitude": 13.0334,
        "longitude": 80.2114,
        "helpline_number": "1930",
        "landline_number": "044-24749001",
        "official_email": "sp.cybercrime-tn@gov.in",
        "nodal_officer_designation": "Superintendent of Police, Cyber Crime Wing",
        "source_url": "https://eservices.tnpolice.gov.in",
        "source_authority": "Tamil Nadu Police Headquarters",
        "verification_status": "officially_listed",
    },
    {
        "name": "Cyber Crime Police Station, Gautam Buddha Nagar",
        "jurisdiction_level": "district",
        "state": "Uttar Pradesh",
        "district": "Gautam Buddha Nagar",
        "city": "Noida",
        "pincode": "201301",
        "address": "Sector 36, Noida, Uttar Pradesh 201301",
        "latitude": 28.5728,
        "longitude": 77.3484,
        "helpline_number": "1930",
        "landline_number": "0120-2570020",
        "official_email": "cyberps.gb-up@nic.in",
        "nodal_officer_designation": "Assistant Commissioner of Police (Cyber Crime)",
        "source_url": "https://uppolice.gov.in",
        "source_authority": "Uttar Pradesh Police",
        "verification_status": "officially_listed",
    },
    {
        "name": "Cyber Crime Police Station, CID West Bengal",
        "jurisdiction_level": "state",
        "state": "West Bengal",
        "district": "Kolkata",
        "city": "Kolkata",
        "pincode": "700027",
        "address": "Bhabani Bhaban, 31 Belvedere Road, Alipore, Kolkata, West Bengal 700027",
        "latitude": 22.5298,
        "longitude": 88.3341,
        "helpline_number": "1930",
        "landline_number": "033-24792626",
        "official_email": "cybercrime-cid@wbpolice.gov.in",
        "nodal_officer_designation": "Special Superintendent of Police, CID West Bengal",
        "source_url": "https://cid.wb.gov.in",
        "source_authority": "West Bengal Police CID",
        "verification_status": "officially_listed",
    },
]

async def seed_locations():
    async with AsyncSessionLocal() as session:
        for item in SEEDED_STATIONS:
            # Check if exists by name and state
            q = select(OfficialLocation).where(
                OfficialLocation.name == item["name"],
                OfficialLocation.state == item["state"]
            )
            res = await session.execute(q)
            existing = res.scalar_one_or_none()
            if existing:
                print(f"Skipping existing station: {item['name']}")
                continue

            loc = OfficialLocation(
                id=uuid.uuid4(),
                name=item["name"],
                jurisdiction_level=item["jurisdiction_level"],
                state=item["state"],
                district=item["district"],
                city=item["city"],
                pincode=item["pincode"],
                address=item["address"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                helpline_number=item.get("helpline_number"),
                landline_number=item.get("landline_number"),
                official_email=item.get("official_email"),
                nodal_officer_designation=item.get("nodal_officer_designation"),
                source_url=item["source_url"],
                source_authority=item["source_authority"],
                verification_status=item["verification_status"],
                last_verified_at=datetime.now(timezone.utc),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(loc)
            print(f"Seeding station: {item['name']} ({item['city']}, {item['state']})")
        
        await session.commit()
        print("All official cyber police stations seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_locations())
