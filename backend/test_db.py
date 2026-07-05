import asyncio
import asyncpg
from core.config import settings

async def run():
    print(f"Connecting to: {settings.DATABASE_URL}")
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    rows = await conn.fetch('SELECT scam_type_code, count(*) FROM cases GROUP BY scam_type_code;')
    print(rows)
    await conn.close()

asyncio.run(run())
