import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case, CaseStatus, CasePriority

SCAM_TYPES = [
    "Phishing", 
    "UPI Fraud", 
    "Identity Theft", 
    "Ransomware", 
    "Credit Card Fraud", 
    "Tech Support Scam",
    "Romance Scam",
    "Investment Fraud"
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad"]
STATES = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu", "West Bengal", "Maharashtra", "Gujarat"]

async def main():
    async with AsyncSessionLocal() as session:
        print("Cleaning up blank cases...")
        from sqlalchemy import delete
        await session.execute(delete(Case).where(Case.scam_type_code.is_(None)))
        await session.commit()
        
        print("Injecting 50 dummy cases...")
        now = datetime.utcnow()
        
        for i in range(50):
            scam_type = random.choice(SCAM_TYPES)
            city_idx = random.randint(0, len(CITIES)-1)
            
            # Random date within last 7 days
            days_ago = random.randint(0, 7)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            new_case = Case(
                case_number=f"INJ-{uuid.uuid4().hex[:8].upper()}",
                scam_text=f"Dummy case for {scam_type}. User reported losing money.",
                scam_type_code=scam_type,
                city=CITIES[city_idx],
                state=STATES[city_idx],
                status=random.choice([CaseStatus.submitted, CaseStatus.investigating, CaseStatus.resolved]),
                priority=random.choice([CasePriority.medium, CasePriority.high, CasePriority.critical]),
                created_at=created_at,
                updated_at=created_at
            )
            session.add(new_case)
            
        await session.commit()
        print("Successfully injected 50 dummy cases!")

if __name__ == "__main__":
    asyncio.run(main())
