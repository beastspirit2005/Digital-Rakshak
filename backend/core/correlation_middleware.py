import uuid
import contextvars
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store correlation ID per asynchronous execution context
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="CORR-SYSTEM"
)


def get_correlation_id() -> str:
    """Retrieves active request/task correlation ID from execution context."""
    return correlation_id_ctx.get()


def set_correlation_id(corr_id: str) -> None:
    """Sets correlation ID in execution context."""
    correlation_id_ctx.set(corr_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    End-to-End Tracing Middleware:
    Extracts or generates unique correlation IDs across all incoming HTTP requests.
    Propagates correlation ID into loggers and HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check incoming headers for existing trace / correlation ID
        incoming_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id")
        )

        if incoming_id and incoming_id.strip():
            corr_id = incoming_id.strip()
        else:
            corr_id = f"CORR-{uuid.uuid4().hex[:12].upper()}"

        # Bind to contextvar for this request
        token = correlation_id_ctx.set(corr_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)
