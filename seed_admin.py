import asyncio
from infrastructure.db.session import AsyncSessionLocal
from domain.models.user import User
from core.security import get_password_hash
from sqlalchemy import select

async def seed_admin():
    async with AsyncSessionLocal() as session:
        # Check if exists
        emails_to_add = ["harshit2500sharm@gmail.com", "harshit2005sharma@gmail.com"]
        for email in emails_to_add:
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                admin_user = User(
                    email=email,
                    full_name="Harshit Sharma",
                    role="admin",
                    is_active=True,
                    is_approved=True,
                    hashed_password=get_password_hash("Welcome@2029")
                )
                session.add(admin_user)
                print(f"Added admin user: {email}")
            else:
                existing_user.role = "admin"
                existing_user.is_approved = True
                existing_user.is_active = True
                existing_user.hashed_password = get_password_hash("Welcome@2029")
                print(f"Updated existing user to admin: {email}")
                
        await session.commit()
        print("Done!")

if __name__ == '__main__':
    asyncio.run(seed_admin())
