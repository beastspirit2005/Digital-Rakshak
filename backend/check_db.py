import asyncio
from sqlalchemy import select
from infrastructure.db.session import engine
from domain.models.case import Case

async def main():
    async with engine.begin() as conn:
        res = await conn.execute(select(Case.scam_type_code))
        print("Scam types in DB:", res.all())

if __name__ == "__main__":
    asyncio.run(main())
