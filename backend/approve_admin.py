import asyncio
from infrastructure.db.session import engine
from sqlalchemy import text

async def approve_admin():
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users SET is_approved = true WHERE email = 'testadmin2@example.com'"))
        print("Admin approved!")

asyncio.run(approve_admin())
