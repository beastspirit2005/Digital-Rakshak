import redis.asyncio as redis
from core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def store_otp(email: str, otp: str, expire_seconds: int = 300):
    await redis_client.setex(f"otp:{email}", expire_seconds, otp)

async def get_otp(email: str):
    return await redis_client.get(f"otp:{email}")

async def delete_otp(email: str):
    await redis_client.delete(f"otp:{email}")

def get_redis():
    return redis_client
