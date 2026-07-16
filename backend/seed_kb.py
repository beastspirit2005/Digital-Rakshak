import asyncio
import sys
from infrastructure.db.session import AsyncSessionLocal
from infrastructure.db.knowledge import KnowledgeBase

async def seed():
    kb = KnowledgeBase()
    async with AsyncSessionLocal() as db:
        await kb.seed_knowledge_base(db)
        print("Done seeding.")

if __name__ == "__main__":
    asyncio.run(seed())
