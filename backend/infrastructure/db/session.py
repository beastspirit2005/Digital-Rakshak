from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings

import ssl
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

# Safely strip ssl query parameters since asyncpg doesn't like them
parsed = urlparse(settings.DATABASE_URL)
query_params = parse_qsl(parsed.query)
query_params = [(k, v) for k, v in query_params if k not in ("ssl", "sslmode")]
db_url = urlunparse(parsed._replace(query=urlencode(query_params)))

# Neon requires SSL for external connections
import os
ssl_context = ssl.create_default_context()
if os.getenv("VERCEL") == "1" or getattr(settings, "ENVIRONMENT", "development") == "production":
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
else:
    # Development mode: permit self-signed or local certificates
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    db_url, 
    echo=False, 
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,        # Recycle connections every 5 minutes to prevent stale idle disconnects on Neon
    pool_size=15,            # Stable concurrent connection pool
    max_overflow=10,         # Burst capacity for high concurrent requests
    pool_timeout=30,         # Fail-fast timeout for connection exhaustion
    connect_args={
        "ssl": ssl_context,
        "prepared_statement_cache_size": 0,  # Disable client-side prepared statement cache
        "statement_cache_size": 0,  # Disable server-side prepared statement cache (required for Neon pooler)
    }
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
