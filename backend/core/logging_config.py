import re
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.config import settings
from core.correlation_middleware import get_correlation_id

# ── PII Sanitisation Regular Expressions (Order-Dependent & Digit-Bounded) ──
# 1. Bearer Tokens & Passwords
SECRET_REGEX = re.compile(
    r"(?i)(bearer\s+[a-zA-Z0-9_\-\.]{15,}|password[\"']?\s*[:=]\s*[\"'][^\"']+[\"'])"
)

# 2. Indian Mobile Numbers: exactly 10 digits starting with 6-9, optionally prefixed by +91 or 0
PHONE_REGEX = re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)")

# 3. 12-digit Indian Aadhaar Numbers (formatted 4-4-4 or 12 consecutive digits)
AADHAAR_REGEX = re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?(?:\d{4}[\s-]?\d{4})(?!\d)")

# 4. Bank Account Numbers (9 to 18 consecutive digits)
ACCOUNT_REGEX = re.compile(r"(?<!\d)\d{9,18}(?!\d)")


def mask_pii(text: str) -> str:
    """
    Sanitizes string inputs by redacting authorization credentials,
    mobile numbers, Aadhaar numbers, and bank account numbers.
    Order is critical: Tokens -> Phones (10-digit) -> Aadhaar (12-digit) -> Accounts (9-18 digit).
    """
    if not isinstance(text, str):
        return str(text)

    # 1. Redact Secrets / Tokens
    scrubbed = SECRET_REGEX.sub("[MASKED_SECRET]", text)

    # 2. Redact Phone numbers first (handles +91 prefix and exactly 10 digits)
    scrubbed = PHONE_REGEX.sub("[MASKED_PHONE]", scrubbed)

    # 3. Redact 12-digit Aadhaar
    scrubbed = AADHAAR_REGEX.sub("[MASKED_AADHAAR]", scrubbed)

    # 4. Redact Bank Account numbers
    scrubbed = ACCOUNT_REGEX.sub("[MASKED_ACCOUNT]", scrubbed)

    return scrubbed


def sanitize_payload(payload: Any) -> Any:
    """Recursively traverses dictionaries / lists to mask confidential PII."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            lower_k = str(k).lower()
            if any(term in lower_k for term in ("password", "token", "secret", "cvv", "otp")):
                sanitized[k] = "[MASKED_CREDENTIAL]"
            elif any(term in lower_k for term in ("account_number", "aadhaar", "phone", "mobile")):
                sanitized[k] = mask_pii(str(v))
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return mask_pii(payload)
    return payload


class StructuredJSONFormatter(logging.Formatter):
    """
    Enterprise Structured JSON Formatter:
    Produces uniform machine-readable JSON logs with ISO-8601 timestamps,
    correlation IDs, service metadata, and automated PII redaction.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Format base message and scrub PII
        raw_message = record.getMessage()
        clean_message = mask_pii(raw_message)

        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "digital-rakshak-backend",
            "environment": getattr(settings, "ENVIRONMENT", "development"),
            "release": getattr(settings, "RELEASE_VERSION", "v2.4.0"),
            "correlation_id": get_correlation_id(),
            "logger": record.name,
            "message": clean_message
        }

        # Optional structured context attributes attached via logger.info("...", extra={...})
        for attr in ("operation", "duration_ms", "case_reference", "error_code", "status_code"):
            val = getattr(record, attr, None)
            if val is not None:
                log_entry[attr] = val

        # Format exception tracebacks if present
        if record.exc_info:
            log_entry["exception"] = mask_pii(self.formatException(record.exc_info))

        return json.dumps(log_entry, ensure_ascii=False)


def setup_structured_logging():
    """Configures structured JSON logging on the root logger."""
    root_logger = logging.getLogger()
    # If handler already exists, replace its formatter
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(StructuredJSONFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJSONFormatter())
        root_logger.addHandler(handler)

    root_logger.setLevel(logging.INFO)
