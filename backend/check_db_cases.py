import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case.case_number, Case.scam_type_code, Case.status))
        for row in res.all():
            print(row)

asyncio.run(main())
