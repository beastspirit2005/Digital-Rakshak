import redis.asyncio as redis
from core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

from infrastructure.db.session import AsyncSessionLocal
from sqlalchemy import select, update
from domain.models.user import User
from datetime import datetime, timedelta

async def store_otp(email: str, otp: str, expire_seconds: int = 300):
    async with AsyncSessionLocal() as session:
        expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
        await session.execute(
            update(User).where(User.email == email).values(otp=otp, otp_expires_at=expires_at)
        )
        await session.commit()

async def get_otp(email: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user and user.otp and user.otp_expires_at and user.otp_expires_at > datetime.utcnow():
            return user.otp
        return None

async def delete_otp(email: str):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.email == email).values(otp=None, otp_expires_at=None)
        )
        await session.commit()

def get_redis():
    return redis_client
