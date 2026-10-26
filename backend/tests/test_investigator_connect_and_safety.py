import pytest
from domain.services.urgency_engine import UrgencyEngine
from domain.services.chat_safety_scanner import ChatSafetyScanner
from infrastructure.pdf.dossier_pdf import generate_fir_dossier_pdf
from api.v1.locations import haversine_km


def test_urgency_engine_critical_digital_arrest():
    result = UrgencyEngine.evaluate(
        incident_type="digital_arrest",
        is_ongoing=True,
        hours_since_incident=0.5,
        estimated_loss_inr=500000.0,
        has_compromised_credentials=True,
    )
    assert result["urgency_level"] == "critical"
    assert len(result["emergency_guidance"]) > 0
    # Confirm 1930 is in emergency guidance
    has_1930 = any("1930" in g["title"] or "1930" in g["description"] for g in result["emergency_guidance"])
    assert has_1930 is True


def test_urgency_engine_standard_past_phishing():
    result = UrgencyEngine.evaluate(
        incident_type="phishing",
        is_ongoing=False,
        hours_since_incident=72.0,
        estimated_loss_inr=0.0,
        has_compromised_credentials=False,
    )
    assert result["urgency_level"] == "standard"


def test_chat_safety_scanner_blocks_otp():
    text = "Please send me your OTP 849201 to verify your account"
    res = ChatSafetyScanner.scan_message(text)
    assert res.is_blocked is True
    assert res.flag == "blocked_credentials"
    assert res.rule in ["RULE_CREDENTIAL_OTP", "RULE_SOLICIT_CREDENTIALS"]
    assert "[REDACTED-SECRET]" in res.sanitized_content


def test_chat_safety_scanner_blocks_upi_pin():
    text = "Enter your UPI PIN 4920 to receive the refund"
    res = ChatSafetyScanner.scan_message(text)
    assert res.is_blocked is True
    assert res.flag == "blocked_credentials"


def test_chat_safety_scanner_warns_recovery_scam():
    text = "We guarantee 100% fund recovery if you pay registration fee to our cyber investigator"
    res = ChatSafetyScanner.scan_message(text)
    assert res.is_blocked is False
    assert res.flag == "flagged_scam"
    assert res.alert_message is not None


def test_chat_safety_scanner_allows_clean_message():
    text = "Hello officer, I submitted my bank account statement and FIR acknowledgment copy."
    res = ChatSafetyScanner.scan_message(text)
    assert res.is_blocked is False
    assert res.flag == "clean"
    assert res.alert_message is None


def test_haversine_math():
    dist = haversine_km(12.9818, 77.5898, 17.4042, 78.4682)
    assert 480.0 <= dist <= 520.0


def test_dossier_pdf_generation():
    pdf_bytes = generate_fir_dossier_pdf(
        reference="DR-2026-99214",
        incident_type="digital_arrest",
        urgency_level="critical",
        incident_date="26 Oct 2026, 06:30 PM UTC",
        victim_name="Ramesh Sharma",
        victim_phone="+91 98765 43210",
        victim_city="Bengaluru",
        victim_state="Karnataka",
        narrative="Complainant was placed under 6-hour video interrogation falsely claiming illegal courier package.",
        estimated_loss_inr=250000.0,
        evidence_items=[
            {
                "filename": "skype_call_screenshot.png",
                "evidence_type": "Screenshot",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            }
        ]
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")
