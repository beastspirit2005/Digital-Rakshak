import asyncio
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import delete

async def clear_cases():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Case))
        await db.commit()
    print("Old cases deleted!")

if __name__ == "__main__":
    asyncio.run(clear_cases())
