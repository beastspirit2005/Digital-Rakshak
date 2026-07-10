import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings
from sqlalchemy import text

async def main():
    print(f"Connecting to {settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql')}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Executing ALTER TABLE...")
        await conn.execute(text("ALTER TABLE users ALTER COLUMN otp TYPE VARCHAR(255);"))
        print("Column altered successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
