import asyncio
import os
import sys
import uuid
import random
from datetime import datetime, timedelta

# Ensure backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

async def seed_counterfeits():
    print("Seeding Counterfeit Intelligence Data into PostgreSQL...")
    from infrastructure.db.session import AsyncSessionLocal
    from domain.models.case import Case, CaseStatus
    from domain.models.user import User
    from sqlalchemy import select

    cities = [
        {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777},
        {"city": "Delhi", "state": "Delhi", "lat": 28.7041, "lng": 77.1025},
        {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639},
        {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
        {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946},
        {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867},
        {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
        {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714}
    ]

    async with AsyncSessionLocal() as db:
        # Get an admin user to assign these to (if any exist)
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin = result.scalar_one_or_none()
        user_id = admin.id if admin else None

        num_cases = 15
        
        for i in range(num_cases):
            loc = random.choice(cities)
            # Add some jitter so they don't overlap completely on the map
            lat = loc["lat"] + random.uniform(-0.08, 0.08)
            lng = loc["lng"] + random.uniform(-0.08, 0.08)
            
            # Simulated Six-Dimension Score for physical counterfeits
            # Note that network/extraction might be different for physical objects
            six_dim_score = {
                "threat": random.uniform(0.85, 0.99),
                "behavior": random.uniform(0.1, 0.3),  # Low cyber behavior
                "network": random.uniform(0.0, 0.2),   # Low digital network linkage
                "integrity": random.uniform(0.8, 0.95),# High evidence integrity
                "impersonation": random.uniform(0.8, 1.0), # High impersonation (fake currency)
                "extraction": 1.0
            }
            
            ai_decision = {
                "decision": "Counterfeit Currency Detected. Missing Intaglio printing and security thread anomalies identified.",
                "confidence": random.uniform(0.85, 0.99),
                "threat_class": "Counterfeit Note",
                "evidence": ["Watermark absent", "Micro-lettering blurred", "Security thread mismatch"],
                "models_used": ["Rakshak-Vision-MobileNetV3"],
                "six_dim_score": six_dim_score,
                "raw_explanation": "Physical currency authentication failed. Anomalies detected in security features.",
                "ztivf_metrics": {"identity_score": 0.1, "evidence_score": 0.95}
            }

            case_num = f"CF-{uuid.uuid4().hex[:6].upper()}"
            
            new_case = Case(
                case_number=case_num,
                submitted_by=user_id,
                scam_text="Uploaded an image of a suspicious ₹500 note received at the local grocery store. The paper feels unusually smooth and the Gandhi watermark is blurry.",
                city=loc["city"],
                state=loc["state"],
                latitude=lat,
                longitude=lng,
                threat_confidence_score=ai_decision["confidence"],
                ai_decision=ai_decision,
                status=CaseStatus.UNDER_REVIEW.value,
                priority="high",
                scam_type_code="Counterfeit Note"
            )
            
            # Backdate them slightly to look realistic
            new_case.created_at = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            
            db.add(new_case)
            
        await db.commit()
        print(f"✅ Successfully seeded {num_cases} Counterfeit cases into the database!")
        print("You can now refresh the Spatial Map on the frontend to see the new Counterfeit layer points.")

if __name__ == "__main__":
    asyncio.run(seed_counterfeits())
