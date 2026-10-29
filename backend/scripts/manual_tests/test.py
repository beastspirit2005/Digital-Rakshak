import asyncio
import sys
sys.path.insert(0, '.')
from infrastructure.db.session import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as db:
        await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR;"))
        await db.commit()
        print("Schema updated!")

if __name__ == "__main__":
    asyncio.run(main())
