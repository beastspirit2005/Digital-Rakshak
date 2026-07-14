import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select
import random

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case))
        cases = res.scalars().all()
        features = []
        for case in cases:
            lat = case.latitude if case.latitude is not None else 21.1458
            lng = case.longitude if case.longitude is not None else 79.0882
            is_unknown = case.latitude is None
            
            if not is_unknown:
                lat += random.uniform(-0.005, 0.005)
                lng += random.uniform(-0.005, 0.005)
            else:
                lat += random.uniform(-1.5, 1.5)
                lng += random.uniform(-1.5, 1.5)
                
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "properties": {
                    "case_id": case.id,
                    "case_number": case.case_number,
                    "type": case.scam_type_code or "Unknown",
                    "status": case.status,
                    "priority": case.priority,
                    "confidence_score": case.threat_confidence_score,
                    "city": case.city,
                    "state": case.state,
                    "is_unknown_location": is_unknown
                }
            })
        print("Successfully processed", len(features), "cases")
        
        # Test FastAPI jsonable_encoder
        from fastapi.encoders import jsonable_encoder
        encoded = jsonable_encoder(features)
        print("Successfully encoded to JSON!")

asyncio.run(main())
