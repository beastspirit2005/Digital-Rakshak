import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(f'HTTP Exception: {exc.status_code} - {exc.detail} on {request.url}')
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})

# OpenTelemetry Setup
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    # Initialize tracing
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry Tracing Enabled.")
except ImportError:
    logger.warning("OpenTelemetry packages not found. Skipping tracing instrumentation.")

import os
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()] if _cors_origins_env else []
_cors_origins += ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]

# Build origin regex: strictly match allowed Vercel preview domains if needed
_origin_patterns = [r"^https://[a-zA-Z0-9-]+\.vercel\.app$"]
# DO NOT blindly allow all http:// origins even in development to prevent local CSRF/SSRF style pivoting

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex="|".join(f"({p})" for p in _origin_patterns),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

from infrastructure.db.session import engine, Base
from domain.models.user import User
from domain.models.case import Case
from domain.models.scam_pattern import ScamPattern
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.cases import router as cases_router
from api.v1.graph import router as graph_router
from api.v1.agents import router as agents_router
from api.v1.takedowns import router as takedowns_router
from api.v1.health import router as health_router
from api.v1.analytics import router as analytics_router
from api.v1.chat import router as chat_router
from api.v1.scan import router as scan_router
from api.v1.settings import router as settings_router
from api.v1.osint import router as osint_router
from api.v1.support import router as support_router
from api.v1.help_chat import router as help_chat_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(cases_router, prefix=f"{settings.API_V1_STR}/cases", tags=["cases"])
app.include_router(graph_router, prefix=f"{settings.API_V1_STR}/graph", tags=["graph"])
app.include_router(agents_router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])
app.include_router(takedowns_router, prefix=f"{settings.API_V1_STR}/takedowns", tags=["takedowns"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}")
app.include_router(health_router, prefix=f"{settings.API_V1_STR}")
app.include_router(chat_router, prefix=f"{settings.API_V1_STR}/cases")
app.include_router(scan_router, prefix=f"{settings.API_V1_STR}")
app.include_router(settings_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(osint_router, prefix=f"{settings.API_V1_STR}/admin/osint", tags=["osint"])
app.include_router(support_router, prefix=f"{settings.API_V1_STR}")
app.include_router(help_chat_router, prefix=f"{settings.API_V1_STR}/help")

def _run_migrations_sync():
    if os.getenv("RUN_MIGRATIONS", "true").lower() != "true":
        logger.info("Skipping migrations. Set RUN_MIGRATIONS=true to run them.")
        return
        
    try:
        from alembic.config import Config
        from alembic import command
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        
        # Override SQLAlchemy URL with database settings
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        logger.info("Running database migrations programmatically...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations successfully applied!")
    except Exception as e:
        logger.error(f"Failed to run programmatic migrations: {e}")

@app.on_event("startup")
async def run_migrations():
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_migrations_sync)


