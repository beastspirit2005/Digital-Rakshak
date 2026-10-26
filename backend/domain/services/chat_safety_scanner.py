"""
Chat Safety & Misconduct Inspection Engine
==========================================
Deterministic high-speed scanning pipeline that inspects all messages and URLs
prior to delivery between citizens and investigators/officers.

Enforces:
1. Hard Credential Blocking: OTPs, UPI PINs, CVV, passwords.
2. Recovery Scam Protection: Advance fee fraud, guaranteed funds recovery claims.
3. SSRF-Safe URL Validation: Blocks private subnets, localhost, and non-HTTP protocols.
"""

import re
import ipaddress
import socket
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel


class ScanResult(BaseModel):
    is_blocked: bool = False
    flag: str = "clean"  # clean, warning_issued, blocked_credentials, flagged_scam
    rule: Optional[str] = None
    alert_message: Optional[str] = None
    sanitized_content: str
    detected_indicators: List[str] = []


class ChatSafetyScanner:
    # 1. Regex patterns for OTP / PIN / Credential solicitation
    OTP_PATTERNS = [
        (re.compile(r"\b(?:otp|one[- ]time[- ]password|verification code)\s*(?:is|:|=)?\s*(\d{4,8})\b", re.IGNORECASE), "RULE_CREDENTIAL_OTP"),
        (re.compile(r"\b(?:share|send|tell|give)\s+(?:me\s+)?(?:your\s+)?(?:otp|pin|password|cvv)\b", re.IGNORECASE), "RULE_SOLICIT_CREDENTIALS"),
        (re.compile(r"\b(?:upi[- ]?pin|mpin|atm[- ]?pin)\s*(?:is|:|=)?\s*(\d{4,6})\b", re.IGNORECASE), "RULE_CREDENTIAL_UPI_PIN"),
        (re.compile(r"\b(?:cvv|cvc)\s*(?:is|:|=)?\s*(\d{3,4})\b", re.IGNORECASE), "RULE_CREDENTIAL_CVV"),
        (re.compile(r"\bpassword\s*(?:is|:|=)\s*([^\s]{6,})\b", re.IGNORECASE), "RULE_CREDENTIAL_PASSWORD"),
    ]

    # 2. Recovery scam patterns (Advance-fee fraud)
    RECOVERY_SCAM_PATTERNS = [
        (re.compile(r"\b(?:100%|guaranteed|full)\s+(?:fund\s+)?(?:recovery|refund)\b", re.IGNORECASE), "RULE_RECOVERY_GUARANTEE"),
        (re.compile(r"\b(?:pay|transfer|deposit)\s+(?:an?\s+)?(?:advance|processing|registration|file|clearance)\s+fee\b", re.IGNORECASE), "RULE_RECOVERY_ADVANCE_FEE"),
        (re.compile(r"\bhack(?:er|ing)\s+(?:into\s+)?(?:the\s+)?(?:scammer|wallet|bank)\b", re.IGNORECASE), "RULE_ILLEGAL_HACKING_OFFER"),
        (re.compile(r"\b(?:crypto|usdt|bitcoin)\s+(?:recovery|tracing\s+service)\s+(?:charges?|fee)\b", re.IGNORECASE), "RULE_CRYPTO_RECOVERY_SCAM"),
    ]

    # 3. URL regex for SSRF inspection
    URL_REGEX = re.compile(
        r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?",
        re.IGNORECASE
    )

    @classmethod
    def is_private_or_reserved_ip(cls, hostname: str) -> bool:
        """
        Resolves hostname and verifies whether it points to a private, loopback,
        or link-local IP address to prevent SSRF vulnerabilities.
        """
        try:
            # Check if hostname is directly an IP
            ip = ipaddress.ip_address(hostname)
            return (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_reserved or
                ip.is_multicast
            )
        except ValueError:
            pass

        # Resolve DNS
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if (
                    ip.is_private or
                    ip.is_loopback or
                    ip.is_link_local or
                    ip.is_reserved or
                    ip.is_multicast
                ):
                    return True
        except (socket.gaierror, socket.herror):
            # If domain cannot be resolved, block it defensively
            return True

        return False

    @classmethod
    def scan_message(cls, content: str) -> ScanResult:
        """
        Executes all inspection rules across text content.
        """
        indicators = []
        sanitized = content

        # Check 1: Credential Harvest / Secrets Guard (Hard Block)
        for pattern, rule_code in cls.OTP_PATTERNS:
            match = pattern.search(content)
            if match:
                indicators.append(f"Credential exposure detected: {rule_code}")
                # Redact matched sensitive fragment
                sanitized = pattern.sub("[REDACTED-SECRET]", sanitized)
                return ScanResult(
                    is_blocked=True,
                    flag="blocked_credentials",
                    rule=rule_code,
                    alert_message="Delivery blocked: Messages containing passwords, OTPs, PINs, or CVVs are strictly forbidden. Digital Rakshak and official police never request authentication secrets.",
                    sanitized_content=sanitized,
                    detected_indicators=indicators
                )

        # Check 2: Recovery Scam / Advance Fee Guard (Warning or Flag)
        for pattern, rule_code in cls.RECOVERY_SCAM_PATTERNS:
            match = pattern.search(content)
            if match:
                indicators.append(f"Suspicious recovery claim: {rule_code}")
                return ScanResult(
                    is_blocked=False,
                    flag="flagged_scam",
                    rule=rule_code,
                    alert_message="Warning: This message contains language associated with advance-fee recovery scams. Official police officers and authorized personnel NEVER demand payment or fees for investigation.",
                    sanitized_content=content,
                    detected_indicators=indicators
                )

        # Check 3: SSRF / Suspicious URL Check
        urls = cls.URL_REGEX.findall(content)
        for u in urls:
            try:
                parsed = urlparse(u)
                if parsed.scheme not in ("http", "https"):
                    return ScanResult(
                        is_blocked=True,
                        flag="blocked_credentials",
                        rule="RULE_FORBIDDEN_PROTOCOL",
                        alert_message="Delivery blocked: Non-standard web protocols are not permitted.",
                        sanitized_content=re.sub(re.escape(u), "[BLOCKED-URL]", sanitized),
                        detected_indicators=[f"Invalid URL protocol: {parsed.scheme}"]
                    )

                host = parsed.hostname
                if not host or cls.is_private_or_reserved_ip(host):
                    return ScanResult(
                        is_blocked=True,
                        flag="blocked_credentials",
                        rule="RULE_SSRF_INTERNAL_IP",
                        alert_message="Delivery blocked: Links pointing to internal network addresses or localhost are forbidden.",
                        sanitized_content=re.sub(re.escape(u), "[BLOCKED-INTERNAL-URL]", sanitized),
                        detected_indicators=[f"Internal/Private host detected: {host}"]
                    )
            except Exception:
                pass

        return ScanResult(
            is_blocked=False,
            flag="clean",
            rule=None,
            alert_message=None,
            sanitized_content=content,
            detected_indicators=[]
        )
