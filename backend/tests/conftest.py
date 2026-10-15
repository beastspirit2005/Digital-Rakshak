import pytest_asyncio
from infrastructure.db.session import engine

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    yield
    await engine.dispose()
