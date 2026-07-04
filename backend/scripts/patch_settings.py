import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.db.session import engine, AsyncSessionLocal
from domain.models.settings import PlatformSettings
import sqlalchemy as sa

async def main():
    async with engine.begin() as conn:
        print("Creating platform_settings table...")
        await conn.run_sync(PlatformSettings.metadata.create_all)
        print("Done!")

    async with AsyncSessionLocal() as session:
        # Check if row 1 exists
        result = await session.execute(sa.select(PlatformSettings).where(PlatformSettings.id == 1))
        row = result.scalar_one_or_none()
        if not row:
            print("Inserting default settings row...")
            session.add(PlatformSettings(id=1, force_local_inference=False, default_ai_mode="auto"))
            await session.commit()
            print("Row inserted.")
        else:
            print("Row already exists.")

if __name__ == "__main__":
    asyncio.run(main())
