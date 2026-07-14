import asyncio
from infrastructure.db.session import AsyncSessionLocal
from domain.models.help_message import HelpMessage, HelpMessageRole

async def main():
    async with AsyncSessionLocal() as db:
        user_msg = HelpMessage(
            session_id="test_session",
            role=HelpMessageRole.USER.value,
            content="Hello"
        )
        db.add(user_msg)
        await db.commit()
        print("Success")

asyncio.run(main())
