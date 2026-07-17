import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case, CaseStatus, CasePriority
from infrastructure.graph.neo4j_client import IntelligenceGraph

# Realistic Indian Cities with Coordinates
CITIES = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777},
    {"city": "Delhi NCR", "state": "Delhi", "lat": 28.7041, "lng": 77.1025},
    {"city": "Bangalore", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946},
    {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
    {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
]

# Threat Vectors to create Syndicates
SYNDICATE_VECTORS = [
    {"type": "PhoneNumber", "value": "+917765432109", "name": "Jamtara Phishing Ring"},
    {"type": "PhoneNumber", "value": "+919876543210", "name": "Fake Customs Scam"},
    {"type": "UPI_ID", "value": "support-refund@okicici", "name": "UPI Refund Scam"},
    {"type": "URL", "value": "http://kyc-update-sbi-portal.com", "name": "SBI KYC Phishing"},
    {"type": "BankAccount", "value": "AC-4455667788", "name": "Mule Account Network"}
]

async def seed_database():
    print("Starting database seeding...")
    
    # 1. Clear existing Neo4j graph if possible, but for safety we'll just add to it.
    graph = IntelligenceGraph()
    
    async with AsyncSessionLocal() as db:
        for i in range(35):
            # Pick a city
            location = random.choice(CITIES)
            
            # Pick a vector to link (80% chance to be part of a syndicate)
            vector = random.choice(SYNDICATE_VECTORS) if random.random() < 0.8 else None
            
            amount = random.uniform(5000, 1500000) # 5k to 15 Lakhs
            
            case_id = uuid.uuid4()
            case_number = f"DR-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"
            
            # Scam Types
            scam_types = ["FIN-PAY-UPI", "SOCIAL-ENGINEERING", "DIGITAL-ARREST", "CUSTOMS-FRAUD", "CRYPTO-SCAM"]
            scam_type = random.choice(scam_types)
            
            # Create Case
            new_case = Case(
                id=case_id,
                case_number=case_number,
                scam_text=f"Victim reported a {scam_type} incident. They were contacted regarding a pending issue and lost Rs. {amount:.2f}.",
                scam_type_code=scam_type,
                city=location["city"],
                state=location["state"],
                latitude=location["lat"] + random.uniform(-0.05, 0.05), # Slight jitter
                longitude=location["lng"] + random.uniform(-0.05, 0.05),
                status=random.choice([CaseStatus.submitted, CaseStatus.investigating, CaseStatus.under_review]),
                priority=random.choice([CasePriority.high, CasePriority.critical]) if amount > 500000 else random.choice([CasePriority.medium, CasePriority.low]),
                estimated_amount=amount,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=random.randint(0, 10))
            )
            
            db.add(new_case)
            await db.commit()
            
            # Link to Neo4j
            if vector:
                await graph.add_case_entity_link(
                    case_id=str(case_id),
                    entity_type=vector["type"],
                    entity_value=vector["value"]
                )
                print(f"Linked {case_number} to {vector['type']} {vector['value']}")
            else:
                print(f"Created isolated case {case_number}")
                
    await graph.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
