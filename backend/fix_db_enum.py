import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE cases SET status = 'under_review' WHERE status = 'UNDER_REVIEW'"))
        await db.commit()
        print("Updated case statuses in DB!")

if __name__ == "__main__":
    asyncio.run(main())
