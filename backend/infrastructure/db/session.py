from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings

import ssl

# Safely strip ssl query parameters since asyncpg doesn't like them
db_url = settings.DATABASE_URL.replace("?sslmode=require", "").replace("?ssl=require", "")

# Neon requires SSL for external connections
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    db_url, 
    echo=True, 
    future=True,
    connect_args={"ssl": ssl_context}
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
