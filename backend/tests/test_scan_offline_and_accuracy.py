import pytest
import uuid
from unittest.mock import MagicMock
from api.v1.scan import live_prevention_scan, ScanRequest
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.ai.ml_client import RakshakCoreClient

@pytest.mark.asyncio
async def test_google_url_verified_legitimate():
    """Verify google.com and its variants match canonical verified domain instantly."""
    scanner = OSINTScanner()
    res1 = scanner.check_url("google.com")
    assert res1["is_safe"] is True
    assert res1["indicator_status"] == "VERIFIED_LEGITIMATE"
    assert res1["matched_domain"] == "google.com"

    res2 = scanner.check_url("https://www.google.com/search?q=test")
    assert res2["is_safe"] is True
    assert res2["indicator_status"] == "VERIFIED_LEGITIMATE"

    req = MagicMock()
    req.client.host = "127.0.0.1"
    scan_res = await live_prevention_scan(request=req, payload=ScanRequest(url="https://www.google.com"), user=None)
    assert scan_res.is_safe is True
    assert scan_res.indicator_status == "VERIFIED_LEGITIMATE"
    assert scan_res.risk_level == "LOW"

@pytest.mark.asyncio
async def test_subdomain_and_path_spoofing_prevention():
    """Verify spoofed domains are not whitelisted via substring bypass."""
    scanner = OSINTScanner()
    # Subdomain spoofing
    res_sub = scanner.check_url("https://google.com.attacker-scam.xyz")
    assert res_sub["indicator_status"] != "VERIFIED_LEGITIMATE"

    # Query path spoofing
    res_path = scanner.check_url("https://attacker.xyz/login?target=google.com")
    assert res_path["indicator_status"] != "VERIFIED_LEGITIMATE"

@pytest.mark.asyncio
async def test_known_malicious_domain_blocked():
    """Verify known phishing infrastructure is immediately classified as KNOWN_MALICIOUS."""
    req = MagicMock()
    req.client.host = "127.0.0.1"
    scan_res = await live_prevention_scan(request=req, payload=ScanRequest(url="https://yono-sbi-update.in/kyc"), user=None)
    assert scan_res.is_safe is False
    assert scan_res.indicator_status == "KNOWN_MALICIOUS"
    assert scan_res.risk_level == "CRITICAL"

def test_raic_core_fallback_safety():
    """Verify RakshakCoreClient.predict does not return a fake UPI Fraud threat when model is unloaded."""
    client = RakshakCoreClient()
    client.model = None
    pred = client.predict("https://google.com")
    assert pred["threat_class"] == "Safe"
    assert pred["confidence"] == 0.0

@pytest.mark.asyncio
async def test_verified_banking_domain():
    """Verify official banking domains match VERIFIED_LEGITIMATE."""
    req = MagicMock()
    req.client.host = "127.0.0.1"
    scan_res = await live_prevention_scan(request=req, payload=ScanRequest(url="https://retail.onlinesbi.sbi/retail/login.htm"), user=None)
    assert scan_res.is_safe is True
    assert scan_res.indicator_status == "VERIFIED_LEGITIMATE"
    assert scan_res.risk_level == "LOW"
