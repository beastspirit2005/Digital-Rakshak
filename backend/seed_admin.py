import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from domain.models.user import User
from core.config import settings

async def seed_admin():
    db_url = settings.DATABASE_URL
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if admin already exists
        # To avoid importing select from sqlalchemy, just create directly if we catch integrity error or just use text query
        
        from sqlalchemy import text
        result = await session.execute(text("SELECT id FROM users WHERE email = 'harshit2500sharma@gmail.com'"))
        row = result.fetchone()
        
        if not row:
            new_user = User(
                email="harshit2500sharma@gmail.com",
                full_name="Harshit Sharma (Admin)",
                role="admin",
                is_active=True,
                is_approved=True
            )
            session.add(new_user)
            await session.commit()
            print("Admin user seeded successfully. Email: harshit2500sharma@gmail.com")
        else:
            print("Admin user already exists. Email: harshit2500sharma@gmail.com")
            
if __name__ == "__main__":
    asyncio.run(seed_admin())
