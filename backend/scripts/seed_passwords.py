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
        admin_pwd = os.getenv("ADMIN_DEFAULT_PASSWORD")
        citizen_pwd = os.getenv("CITIZEN_DEFAULT_PASSWORD")
        if not admin_pwd or not citizen_pwd:
            raise ValueError("Both ADMIN_DEFAULT_PASSWORD and CITIZEN_DEFAULT_PASSWORD environment variables must be set.")
        
        admin_hash = get_password_hash(admin_pwd)
        citizen_hash = get_password_hash(citizen_pwd)

        for u in users:
            if u.role == 'admin':
                u.hashed_password = admin_hash
                print(f"Updated password for Admin {u.full_name} ({u.email})")
            elif u.role == 'citizen':
                u.hashed_password = citizen_hash
                print(f"Updated password for Citizen {u.full_name} ({u.email})")
                
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
