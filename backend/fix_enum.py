import asyncio
import sys
from infrastructure.db.session import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.begin() as conn:
            try:
                await conn.execute(text("CREATE TYPE casestatus AS ENUM ('submitted', 'assigned', 'under_review', 'investigating', 'escalated', 'resolved', 'closed');"))
                print("Created casestatus enum")
            except Exception as e:
                print("casestatus error:", e)
            
            try:
                await conn.execute(text("CREATE TYPE casepriority AS ENUM ('low', 'medium', 'high', 'critical');"))
                print("Created casepriority enum")
            except Exception as e:
                print("casepriority error:", e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
