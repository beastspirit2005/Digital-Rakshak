import logging
from typing import Optional, Dict, Any

from core.config import settings
from core.correlation_middleware import get_correlation_id
from core.logging_config import mask_pii, sanitize_payload

logger = logging.getLogger(__name__)

# Sensitive header keys that must NEVER be forwarded to external APM
STRIPPED_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-cron-secret",
    "x-api-key"
}


def sentry_before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Sentry Event Sanitisation Gate:
    1. Redacts PII (Aadhaar, accounts, phone numbers) from exception values and messages.
    2. Strips authorization credentials, cookies, and tokens from request context.
    3. Injects correlation ID tag for distributed traceability.
    """
    # 1. Attach active correlation ID
    tags = event.setdefault("tags", {})
    tags["correlation_id"] = get_correlation_id()
    tags["environment"] = getattr(settings, "ENVIRONMENT", "production")

    # 2. Sanitize request context if present
    request_data = event.get("request", {})
    if request_data:
        # Strip sensitive headers
        headers = request_data.get("headers", {})
        if isinstance(headers, dict):
            request_data["headers"] = {
                k: "[STRIPPED]" if k.lower() in STRIPPED_HEADERS else v
                for k, v in headers.items()
            }

        # Clear query string to prevent token leaks
        if "query_string" in request_data:
            request_data["query_string"] = "[REDACTED]"

        # Scrub request body data if any was captured
        if "data" in request_data:
            request_data["data"] = sanitize_payload(request_data["data"])

    # 3. Sanitize exception messages and stack trace values
    exception_data = event.get("exception", {})
    values = exception_data.get("values", [])
    for val in values:
        if "value" in val and isinstance(val["value"], str):
            val["value"] = mask_pii(val["value"])

    # 4. Sanitize top-level message if present
    if "message" in event and isinstance(event["message"], str):
        event["message"] = mask_pii(event["message"])

    return event


def sentry_before_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sanitizes breadcrumb messages and HTTP request breadcrumbs."""
    if "message" in crumb and isinstance(crumb["message"], str):
        crumb["message"] = mask_pii(crumb["message"])
    if "data" in crumb:
        crumb["data"] = sanitize_payload(crumb["data"])
    return crumb


def init_sentry() -> bool:
    """
    Initializes Sentry monitoring if SENTRY_DSN is configured and SDK is installed.
    Returns True if initialized, False otherwise.
    """
    dsn = getattr(settings, "SENTRY_DSN", None)
    if not dsn or not dsn.strip():
        logger.info("SENTRY_DSN not configured. Sentry exception monitoring is disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn.strip(),
            environment=getattr(settings, "ENVIRONMENT", "production"),
            release=getattr(settings, "RELEASE_VERSION", "v2.4.0"),
            send_default_pii=False,
            traces_sample_rate=0.1,
            before_send=sentry_before_send,
            before_breadcrumb=sentry_before_breadcrumb,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration()
            ]
        )
        logger.info("Sentry monitoring successfully initialized with PII sanitisation gate.")
        return True

    except ImportError:
        logger.warning("sentry-sdk package is not installed. Sentry initialization skipped.")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
        return False
