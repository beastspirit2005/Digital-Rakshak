import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def _run_migrations_sync():
    if os.getenv("RUN_MIGRATIONS", "false").lower() != "true":
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_migrations_sync)
    
    if getattr(settings, "STREAM_CONSUMER_ENABLED", False):
        from runtime.stream_consumer import StreamConsumer
        consumer = StreamConsumer()
        asyncio.create_task(consumer.run())
        logger.info("StreamConsumer background worker started.")

    # Start Supabase anti-pause keepalive daemon (every 12 hours)
    if getattr(settings, "SUPABASE_URL", None):
        from runtime.supabase_keepalive import supabase_keepalive
        asyncio.create_task(supabase_keepalive.start_daemon(interval_seconds=43200))
        logger.info("Supabase keep-alive anti-pause daemon registered.")

    yield

    try:
        from infrastructure.event_bus.redis_streams import event_bus
        await event_bus.close()
    except Exception as exc:
        logger.warning(f"Error during shutdown event bus cleanup: {exc}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import re

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()] if _cors_origins_env else []
_cors_origins += [
    "http://localhost:3000", 
    "http://localhost:3001", 
    "http://127.0.0.1:3000", 
    "http://127.0.0.1:3001",
    os.getenv("FRONTEND_URL", "http://localhost:3000")
]
_origin_patterns = [
    r"^https://rakshak-backend(-[a-zA-Z0-9-]+)?\.vercel\.app$",
    r"^https://digital-?rakshak(-[a-zA-Z0-9-]+)?\.vercel\.app$",
    r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):300[01]$",
]

def _is_origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    if origin in _cors_origins:
        return True
    return any(bool(re.match(p, origin)) for p in _origin_patterns)

def _cors_headers_for_request(request: Request) -> dict:
    origin = request.headers.get("origin")
    if origin and _is_origin_allowed(origin):
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true"
        }
    return {}

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    messages = []
    for err in raw_errors:
        loc = [str(l) for l in err.get("loc", []) if l != "body"]
        field = " -> ".join(loc)
        msg = str(err.get("msg", "Invalid input")).replace("Value error, ", "")
        messages.append(f"{field}: {msg}" if field else msg)
    clean_message = "; ".join(messages) if messages else "Validation failed"
    logger.warning(f"Validation error on {request.url}: {clean_message}")
    return JSONResponse(
        status_code=422,
        content={"detail": clean_message, "errors": jsonable_encoder(raw_errors)},
        headers=_cors_headers_for_request(request)
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} on {request.url}")
    return JSONResponse(
        status_code=exc.status_code, 
        content={'detail': exc.detail},
        headers=_cors_headers_for_request(request)
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url}: {exc}", exc_info=True)
    is_cloud = os.environ.get("VERCEL") == "1"
    err_detail = "Internal Server Error" if is_cloud else str(exc)
    return JSONResponse(
        status_code=500, 
        content={'detail': "Internal Server Error", 'error': err_detail},
        headers=_cors_headers_for_request(request)
    )

# OpenTelemetry Setup
try:
    if os.getenv("ENABLE_CONSOLE_TRACING", "false").lower() == "true":
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


from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 30 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_upload_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request entity too large. Maximum permitted request size is 30MB."},
                        headers=_cors_headers_for_request(request)
                    )
            except ValueError:
                pass
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware, max_upload_size=30 * 1024 * 1024)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex="|".join(f"({p})" for p in _origin_patterns),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
from api.v1.mock_apis import router as mock_apis_router
from api.v1.evidence import router as evidence_router
from api.v1.stream_router import router as stream_router
from api.v1.entities import router as entities_router
from api.v1.cache_router import router as cache_router
from api.v1.transactions import router as transactions_router
from api.v1.b2b import router as b2b_router
from api.v1.billing import router as billing_router
from api.v1.assistance import router as assistance_router
from api.v1.admin_triage import router as admin_triage_router
from api.v1.locations import router as locations_router
from api.v1.chat_safety import router as chat_safety_router
from api.v1.admin_disputes import router as admin_disputes_router
from api.v1.police_proximity import router as police_proximity_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(cases_router, prefix=f"{settings.API_V1_STR}/cases", tags=["cases"])
app.include_router(graph_router, prefix=f"{settings.API_V1_STR}/graph", tags=["graph"])
app.include_router(agents_router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])
app.include_router(takedowns_router, prefix=f"{settings.API_V1_STR}/takedowns", tags=["takedowns"])
app.include_router(transactions_router, prefix=f"{settings.API_V1_STR}/transactions", tags=["transactions"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}")
app.include_router(health_router, prefix=f"{settings.API_V1_STR}")
app.include_router(chat_router, prefix=f"{settings.API_V1_STR}/cases")
app.include_router(scan_router, prefix=f"{settings.API_V1_STR}")
app.include_router(settings_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(osint_router, prefix=f"{settings.API_V1_STR}/admin/osint", tags=["osint"])
app.include_router(support_router, prefix=f"{settings.API_V1_STR}")
app.include_router(help_chat_router, prefix=f"{settings.API_V1_STR}/help")
app.include_router(mock_apis_router, prefix=f"{settings.API_V1_STR}/mock-apis", tags=["mock_apis"])
app.include_router(evidence_router, prefix=f"{settings.API_V1_STR}")
app.include_router(stream_router, prefix=f"{settings.API_V1_STR}")
app.include_router(entities_router, prefix=f"{settings.API_V1_STR}")
app.include_router(cache_router, prefix=f"{settings.API_V1_STR}")
app.include_router(b2b_router, prefix=f"{settings.API_V1_STR}")
app.include_router(billing_router, prefix=f"{settings.API_V1_STR}")
app.include_router(assistance_router, prefix=f"{settings.API_V1_STR}")
app.include_router(admin_triage_router, prefix=f"{settings.API_V1_STR}")
app.include_router(locations_router, prefix=f"{settings.API_V1_STR}")
app.include_router(chat_safety_router, prefix=f"{settings.API_V1_STR}")
app.include_router(admin_disputes_router, prefix=f"{settings.API_V1_STR}")
app.include_router(police_proximity_router, prefix=f"{settings.API_V1_STR}")




