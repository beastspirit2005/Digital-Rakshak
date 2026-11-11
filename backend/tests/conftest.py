import pytest_asyncio
from infrastructure.db.session import engine

@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db_engine():
    yield
    try:
        await engine.dispose()
    except Exception:
        pass
