"""Set a known password for admin users directly via SQLAlchemy."""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from core.security import get_password_hash
from sqlalchemy import select, update

async def main():
    pwd_hash = get_password_hash("Admin@123")
    print(f"Generated hash: {pwd_hash[:20]}...")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(User)
            .where(User.email.in_(["harshit2500sharma@gmail.com", "admin@rakshak.gov.in"]))
            .values(hashed_password=pwd_hash)
        )
        print(f"Updated {result.rowcount} admin users with password Admin@123")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
