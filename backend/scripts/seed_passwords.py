import asyncio
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.db.session import AsyncSessionLocal
from sqlalchemy import text
from sqlalchemy.future import select
from domain.models.user import User
from core.security import get_password_hash

async def main():
    async with AsyncSessionLocal() as db:
        # Step 1: Add the hashed_password column if it doesn't exist
        print("Altering schema to add hashed_password column...")
        await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR;"))
        await db.commit()
        
        # Step 2: Query for Harshit users
        print("Seeding passwords...")
        res = await db.execute(select(User).filter(User.full_name.ilike('%Harshit%')))
        users = res.scalars().all()
        
        for u in users:
            if u.role == 'admin':
                u.hashed_password = get_password_hash("Welcome@2005")
                print(f"Updated password for Admin {u.full_name} ({u.email})")
            elif u.role == 'citizen':
                u.hashed_password = get_password_hash("Welcome@2029")
                print(f"Updated password for Citizen {u.full_name} ({u.email})")
                
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
