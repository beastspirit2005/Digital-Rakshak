import asyncio
import sqlalchemy
from infrastructure.db.session import engine, AsyncSessionLocal
from infrastructure.db.knowledge import Base as KnowledgeBaseModel, KnowledgeBase

async def setup():
    print("Creating vector extension...")
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text('CREATE EXTENSION IF NOT EXISTS vector;'))
        
    print("Dropping old tables...")
    async with engine.begin() as conn:
        await conn.run_sync(KnowledgeBaseModel.metadata.drop_all)
        
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(KnowledgeBaseModel.metadata.create_all)
    
    print("Seeding data...")
    async with AsyncSessionLocal() as session:
        kb = KnowledgeBase()
        await kb.seed_knowledge_base(session)
        
    print("Done!")

if __name__ == "__main__":
    asyncio.run(setup())
