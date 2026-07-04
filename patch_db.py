import asyncio
from infrastructure.db.session import AsyncSessionLocal
from sqlalchemy import text

async def patch_db():
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN otp VARCHAR(10);"))
            await session.execute(text("ALTER TABLE users ADD COLUMN otp_expires_at TIMESTAMP;"))
            await session.commit()
            print("Successfully added OTP columns to users table!")
        except Exception as e:
            print("Columns might already exist or error:", e)

if __name__ == '__main__':
    asyncio.run(patch_db())
