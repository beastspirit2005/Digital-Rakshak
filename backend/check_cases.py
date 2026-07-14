import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case.case_number))
        cases = res.scalars().all()
        print(cases)

asyncio.run(main())
