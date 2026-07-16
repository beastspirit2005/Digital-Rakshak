import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case).where(Case.case_number == 'CAS-4F9C7B46'))
        c = res.scalar_one_or_none()
        if c:
            # Try to get from ai_decision
            if c.ai_decision and isinstance(c.ai_decision, dict):
                stype = c.ai_decision.get("scam_type_classification")
                if stype:
                    c.scam_type_code = stype
                    print(f"Fixed from ai_decision: {stype}")
            
            if not c.scam_type_code:
                c.scam_type_code = "Cyber Fraud"
                print("Set default: Cyber Fraud")
            
            await db.commit()
            print("Saved!")
        else:
            print("Case not found")

asyncio.run(main())
