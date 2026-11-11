import pytest
import io
from PIL import Image
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.osint.apk_scanner import APKScanner
from infrastructure.osint.qr_decoder import QRDecoder


def test_url_scanner_malicious_and_legitimate():
    """Verify URL engine correctly detects known malicious infrastructure and verified domains."""
    scanner = OSINTScanner()

    # 1. Known malicious phishing domain
    bad_res = scanner.check_url("https://update-pan-kyc.com/login")
    assert bad_res["is_safe"] is False
    assert bad_res["risk_level"] == "CRITICAL"
    assert bad_res["indicator_status"] == "KNOWN_MALICIOUS"

    # 2. Verified official banking domain
    good_res = scanner.check_url("https://retail.onlinesbi.sbi/personal")
    assert good_res["is_safe"] is True
    assert good_res["risk_level"] == "LOW"
    assert good_res["indicator_status"] == "VERIFIED_LEGITIMATE"

    # 3. Subdomain spoofing prevention (google.com.attacker.com must NOT match google.com)
    spoofed = scanner.check_url("https://google.com.phishing-attacker.top/login")
    assert spoofed["indicator_status"] != "VERIFIED_LEGITIMATE"


def test_upi_scanner_impersonation_and_nodal():
    """Verify UPI scanner flags deceptive lures while validating official NPCI handles."""
    scanner = OSINTScanner()

    # 1. Deceptive cashback lure
    bad_upi = scanner.scan_upi("instant.cashback.reward@paytm")
    assert bad_upi["flagged"] is True
    assert bad_upi["risk_level"] == "CRITICAL"
    assert bad_upi["indicator_status"] == "KNOWN_MALICIOUS"

    # 2. Deceptive KYC impersonation
    kyc_upi = scanner.scan_upi("sbi-kyc-desk@okaxis")
    assert kyc_upi["flagged"] is True
    assert kyc_upi["risk_level"] == "CRITICAL"

    # 3. Verified official NPCI institutional handle
    good_upi = scanner.scan_upi("central.utility@npci")
    assert good_upi["flagged"] is False
    assert good_upi["indicator_status"] == "VERIFIED_LEGITIMATE"


def test_phone_scanner_vishing_and_helpline():
    """Verify phone scanner intercepts high-risk international spoofing and validates national emergency numbers."""
    scanner = OSINTScanner()

    # 1. High-risk WhatsApp vishing prefix (+92)
    bad_phone = scanner.scan_phone("+92 300 1234567")
    assert bad_phone["flagged"] is True
    assert bad_phone["risk_level"] == "CRITICAL"
    assert "High-risk foreign country code" in bad_phone["threat"]

    # 2. Official National Cybercrime Helpline 1930
    helpline = scanner.scan_phone("1930")
    assert helpline["flagged"] is False
    assert helpline["indicator_status"] == "VERIFIED_LEGITIMATE"
    assert helpline["risk_level"] == "LOW"

    # 3. Valid standard 10-digit Indian mobile number
    standard = scanner.scan_phone("+91 9876543210")
    assert standard["flagged"] is False
    assert standard["indicator_status"] == "UNKNOWN_UNVERIFIED"


def test_text_scanner_coercive_digital_arrest():
    """Verify SMS/Text scanner intercepts coercive legal extortion (Digital Arrest) patterns."""
    scanner = OSINTScanner()

    # 1. Coercive Digital Arrest message
    scam_msg = "Your FedEx parcel containing illegal drugs has been seized. CBI officer is on Skype video call. Pay fine to avoid arrest."
    scam_res = scanner.scan_text(scam_msg)
    assert len(scam_res["counterfeit_warnings"]) >= 1
    assert scam_res["indicator_status"] in ["SUSPICIOUS", "KNOWN_MALICIOUS"]

    # 2. Benign conversational message
    clean_msg = "Hey Rahul, let us meet for lunch at the cafeteria at 1 PM."
    clean_res = scanner.scan_text(clean_msg)
    assert len(scam_res["flagged_urls"]) == 0
    assert clean_res["risk_level"] == "LOW"
    assert clean_res["indicator_status"] == "UNKNOWN_UNVERIFIED"


def test_apk_scanner_trojan_permissions():
    """Verify APK scanner flags banking trojan permissions."""
    apk_scanner = APKScanner()
    assert "android.permission.BIND_ACCESSIBILITY_SERVICE" in apk_scanner.DANGEROUS_PERMISSIONS
    assert "android.permission.RECEIVE_SMS" in apk_scanner.DANGEROUS_PERMISSIONS
    assert "android.permission.SYSTEM_ALERT_WINDOW" in apk_scanner.DANGEROUS_PERMISSIONS


@pytest.mark.asyncio
async def test_qr_decoder_resilience():
    """Verify QR decoder gracefully handles non-QR images without crashing."""
    decoder = QRDecoder()

    # Create synthetic blank PNG image
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    blank_bytes = buf.getvalue()

    # Synchronous decoder should return None for blank image (no crash)
    result = decoder.decode_image(blank_bytes)
    assert result is None

    # Async decoder should return None without crashing
    async_result = await decoder.decode_image_async(blank_bytes)
    assert async_result is None
