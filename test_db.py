import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from infrastructure.db.session import SessionLocal
from domain.models.user import User
from core.security import verify_password
from sqlalchemy.future import select

async def check():
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"User: {u.email} | Approved: {u.is_approved} | Active: {u.is_active} | HashedPwd: {u.hashed_password}")

if __name__ == "__main__":
    asyncio.run(check())
