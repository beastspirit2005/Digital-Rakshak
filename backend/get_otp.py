import asyncio
from sqlalchemy import select
from infrastructure.db.session import async_session_maker
from domain.models.user import User

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == 'harshit2500sharma@gmail.com'))
        u = result.scalars().first()
        if u:
            print(f'User OTP is: {u.otp}')
        else:
            print('User not found')

asyncio.run(main())
