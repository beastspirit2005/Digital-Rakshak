import asyncio
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == 'harshit2005sharma@gmail.com'))
        user = result.scalar_one_or_none()
        if user:
            print(f'User found: {user.email}, Approved: {user.is_approved}')
        else:
            print('User NOT FOUND in database.')

if __name__ == '__main__':
    asyncio.run(main())
