import json
import logging
from core.correlation_middleware import get_correlation_id, set_correlation_id
from core.logging_config import (
    mask_pii,
    sanitize_payload,
    StructuredJSONFormatter
)
from core.sentry_integration import sentry_before_send, sentry_before_breadcrumb


# ── 1. PII Scrubbing Tests ────────────────────────────────────────────────

def test_pii_masking_aadhaar():
    """Validates redaction of 12-digit Indian Aadhaar numbers."""
    samples = [
        "Victim Aadhaar: 2345 6789 0123 provided in complaint",
        "Aadhaar 987654321098 linked to KYC",
        "Number 4567-8901-2345 stored"
    ]
    for sample in samples:
        masked = mask_pii(sample)
        assert "[MASKED_AADHAAR]" in masked
        assert "2345 6789 0123" not in masked
        assert "987654321098" not in masked
        assert "4567-8901-2345" not in masked


def test_pii_masking_bank_account():
    """Validates redaction of 9 to 18 digit bank account numbers."""
    text = "Beneficiary bank account 50100234567890 at HDFC Bank"
    masked = mask_pii(text)
    assert "[MASKED_ACCOUNT]" in masked
    assert "50100234567890" not in masked


def test_pii_masking_indian_phone():
    """Validates redaction of Indian mobile numbers."""
    samples = [
        "Call fraudster at +919876543210 immediately",
        "WhatsApp reported from 9876543210",
        "Dialed 09876543210 during phishing"
    ]
    for sample in samples:
        masked = mask_pii(sample)
        assert "[MASKED_PHONE]" in masked
        assert "9876543210" not in masked


def test_pii_masking_bearer_tokens_and_passwords():
    """Validates redaction of auth tokens and passwords."""
    text = "Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0 with password='SuperSecretPassword123'"
    masked = mask_pii(text)
    assert "[MASKED_SECRET]" in masked
    assert "SuperSecretPassword123" not in masked
    assert "eyJhbGciOi" not in masked


def test_sanitize_payload_recursive():
    """Validates recursive dict / list sanitization."""
    payload = {
        "case_id": "CAS-1234",
        "user": {
            "phone": "+919876543210",
            "password": "ClearTextPassword!",
            "account_number": "1234567890123456"
        },
        "evidence_files": ["doc1.pdf", "doc2.jpg"],
        "nested_list": [
            {"aadhaar": "2345 6789 0123"}
        ]
    }
    sanitized = sanitize_payload(payload)

    assert sanitized["user"]["password"] == "[MASKED_CREDENTIAL]"
    assert "[MASKED_PHONE]" in sanitized["user"]["phone"]
    assert "[MASKED_ACCOUNT]" in sanitized["user"]["account_number"]
    assert "[MASKED_AADHAAR]" in sanitized["nested_list"][0]["aadhaar"]
    assert sanitized["case_id"] == "CAS-1234"


# ── 2. Structured JSON Logger Tests ───────────────────────────────────────

def test_structured_json_formatter_output():
    """Validates that log records are formatted into compliant JSON with correlation IDs."""
    formatter = StructuredJSONFormatter()
    set_correlation_id("CORR-TEST-OBSERVABILITY-01")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_observability.py",
        lineno=42,
        msg="Error processing transaction for account 50100234567890 with phone 9876543210",
        args=(),
        exc_info=None
    )
    record.operation = "OUTBOX_DISPATCH"
    record.duration_ms = 350
    record.error_code = "BANK_504_TIMEOUT"

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    # Invariants
    assert data["service"] == "digital-rakshak-backend"
    assert data["level"] == "ERROR"
    assert data["correlation_id"] == "CORR-TEST-OBSERVABILITY-01"
    assert data["operation"] == "OUTBOX_DISPATCH"
    assert data["duration_ms"] == 350
    assert data["error_code"] == "BANK_504_TIMEOUT"
    assert "timestamp" in data

    # Verify PII was redacted from message
    assert "[MASKED_ACCOUNT]" in data["message"]
    assert "[MASKED_PHONE]" in data["message"]
    assert "50100234567890" not in data["message"]
    assert "9876543210" not in data["message"]


# ── 3. Sentry Scrubbing Gate Tests ────────────────────────────────────────

def test_sentry_before_send_strips_headers_and_masks_pii():
    """
    Verifies that Sentry before_send strips sensitive HTTP headers,
    redacts query strings, attaches correlation tags, and scrubs stack trace values.
    """
    set_correlation_id("CORR-SENTRY-TRACE-99")

    raw_event = {
        "request": {
            "headers": {
                "Authorization": "Bearer secret_jwt_token_here_123456789",
                "Cookie": "access_token=jwt.cookie.val",
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            },
            "query_string": "token=secret_in_url&case=123",
            "data": {
                "account_number": "12345678901234",
                "password": "mypassword"
            }
        },
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "Failed transfer to account 50100987654321 for Aadhaar 2345 6789 0123"
                }
            ]
        },
        "message": "Alert failed for phone 9876543210"
    }

    sanitized_event = sentry_before_send(raw_event, hint={})

    # Assert tags
    assert sanitized_event["tags"]["correlation_id"] == "CORR-SENTRY-TRACE-99"

    # Assert stripped headers
    headers = sanitized_event["request"]["headers"]
    assert headers["Authorization"] == "[STRIPPED]"
    assert headers["Cookie"] == "[STRIPPED]"
    assert headers["User-Agent"] == "Mozilla/5.0"

    # Assert redacted query string
    assert sanitized_event["request"]["query_string"] == "[REDACTED]"

    # Assert scrubbed request body
    assert sanitized_event["request"]["data"]["password"] == "[MASKED_CREDENTIAL]"
    assert "[MASKED_ACCOUNT]" in sanitized_event["request"]["data"]["account_number"]

    # Assert scrubbed exception values
    exc_value = sanitized_event["exception"]["values"][0]["value"]
    assert "[MASKED_ACCOUNT]" in exc_value
    assert "[MASKED_AADHAAR]" in exc_value
    assert "50100987654321" not in exc_value
    assert "2345 6789 0123" not in exc_value

    # Assert scrubbed top-level message
    assert "[MASKED_PHONE]" in sanitized_event["message"]
    assert "9876543210" not in sanitized_event["message"]


def test_sentry_before_breadcrumb_sanitizes_message():
    """Verifies breadcrumb messages have PII scrubbed."""
    crumb = {
        "message": "User called +919876543210 with account 123456789012",
        "data": {"password": "test_password"}
    }
    sanitized = sentry_before_breadcrumb(crumb, hint={})
    assert "[MASKED_PHONE]" in sanitized["message"]
    assert "[MASKED_ACCOUNT]" in sanitized["message"]
    assert sanitized["data"]["password"] == "[MASKED_CREDENTIAL]"
