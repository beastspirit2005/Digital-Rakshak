import asyncio
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from infrastructure.graph.neo4j_client import IntelligenceGraph
from core.config import settings

# Mock diverse cases
CASES_DATA = [
    # --- GANG 1: Digital Arrest Syndicate (Operating PAN India, using same Phone & UPI) ---
    {
        "city": "Delhi", "state": "Delhi", "lat": 28.7041, "lng": 77.1025,
        "text": "I got a Skype call from +919876543210 saying they are CBI. They said my Aadhaar is linked to money laundering. I transferred Rs 50,000 to cbi.official@sbi to avoid arrest.",
        "phone": "+919876543210", "upi": "cbi.official@sbi", "scam": "Digital Arrest"
    },
    {
        "city": "Bangalore", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946,
        "text": "Received a call from CBI officer on +919876543210. Claimed I was implicated in a drug case. I panicked and paid 1 lakh to cbi.official@sbi.",
        "phone": "+919876543210", "upi": "cbi.official@sbi", "scam": "Digital Arrest"
    },
    {
        "city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707,
        "text": "Fake police called from +919876543210. Threatened to arrest me for a parcel. Paid fine to cbi.official@sbi.",
        "phone": "+919876543210", "upi": "cbi.official@sbi", "scam": "Digital Arrest"
    },

    # --- GANG 2: FedEx/Customs Scam (Using URL and Bank Account) ---
    {
        "city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777,
        "text": "Got SMS about detained FedEx parcel. Clicked fedex-tracking-urgent.com and paid Rs 5000 to Account No 1122334455.",
        "url": "fedex-tracking-urgent.com", "bank": "1122334455", "scam": "FedEx Scam"
    },
    {
        "city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567,
        "text": "Customs officer called saying parcel has passports. Checked fedex-tracking-urgent.com. Paid 20,000 to Account 1122334455.",
        "url": "fedex-tracking-urgent.com", "bank": "1122334455", "scam": "FedEx Scam"
    },
    {
        "city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714,
        "text": "Parcel held at customs. Fake site fedex-tracking-urgent.com asked for clearance fee to account 1122334455.",
        "url": "fedex-tracking-urgent.com", "bank": "1122334455", "scam": "FedEx Scam"
    },

    # --- GANG 3: Electricity Disconnection (Using Phone number) ---
    {
        "city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639,
        "text": "SMS: 'Electricity will be disconnected at 9PM. Call officer on +917766554433.' I called and they drained my account.",
        "phone": "+917766554433", "scam": "Electricity Scam"
    },
    {
        "city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867,
        "text": "Power cut message. Contacted +917766554433. They made me install AnyDesk.",
        "phone": "+917766554433", "scam": "Electricity Scam"
    },
    {
        "city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873,
        "text": "Received electricity disconnection alert. Called +917766554433 and lost 50k.",
        "phone": "+917766554433", "scam": "Electricity Scam"
    },
]

async def seed_cases():
    print("Seeding Diverse Pan-India Cases...")
    graph = IntelligenceGraph()
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from domain.models.user import User
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        mock_user_id = str(user.id) if user else "00000000-0000-0000-0000-000000000000"
        
        for c in CASES_DATA:
            case_id = f"CAS-{uuid.uuid4().hex[:8].upper()}"
            
            # 1. Generate Mock AI Decision
            ai_decision = {
                "decision": "Fraudulent",
                "confidence": 0.98,
                "reasoning": f"AI identified a known {c['scam']} pattern matching OSINT intelligence. Overlapping IoCs detected across multiple states.",
                "extracted_entities": {
                    "phone_numbers": [c.get("phone")] if c.get("phone") else [],
                    "urls": [c.get("url")] if c.get("url") else [],
                    "upi_ids": [c.get("upi")] if c.get("upi") else [],
                    "bank_accounts": [c.get("bank")] if c.get("bank") else []
                },
                "scam_type_classification": c["scam"],
                "preventative_measures": [
                    f"Immediately block {c.get('upi') or c.get('bank') or c.get('phone')} at the central nodal level.",
                    "Issue public advisory against this Modus Operandi."
                ]
            }
            
            # 2. Insert into Postgres
            new_case = Case(
                case_number=case_id,
                submitted_by=mock_user_id,
                scam_text=c["text"],
                city=c["city"],
                state=c["state"],
                latitude=c["lat"],
                longitude=c["lng"],
                threat_confidence_score=0.98,
                ai_decision=ai_decision,
                status="under_review"
            )
            db.add(new_case)
            
            # 3. Insert into Neo4j
            if c.get("phone"):
                await graph.add_case_entity_link(case_id, "PhoneNumber", c["phone"])
            if c.get("upi"):
                await graph.add_case_entity_link(case_id, "UPI_ID", c["upi"])
            if c.get("url"):
                await graph.add_case_entity_link(case_id, "URL", c["url"])
            if c.get("bank"):
                await graph.add_case_entity_link(case_id, "BankAccount", c["bank"])
                
            print(f"Created Case {case_id} in {c['city']} ({c['scam']})")
            
        await db.commit()
    await graph.close()
    print("Successfully seeded diverse case data into Postgres and Neo4j!")

if __name__ == "__main__":
    asyncio.run(seed_cases())
