import pytest
from domain.services.financial_loss_extractor import extract_financial_loss

def test_bank_switch_escalation_extraction():
    text = (
        "Bank Switch Escalation: Flagged Transaction TXN-FRAUD-E27C6E. "
        "Remitter Account ACC-TEST-VICTIM transferred INR 95,000.00 to Beneficiary ACC-TEST-MULE. "
        "Reason: Sudden High-Value Transfer."
    )
    result = extract_financial_loss(text)
    assert result == 95000.0

def test_various_currency_formats():
    assert extract_financial_loss("I lost Rs. 45,000 in a telegram task scam") == 45000.0
    assert extract_financial_loss("Scammer demanded ₹75,000 via Google Pay") == 75000.0
    assert extract_financial_loss("Transferred rupees 12500 immediately") == 12500.0
    assert extract_financial_loss("Debited INR 5000 from my SBI account") == 5000.0

def test_indian_magnitude_words():
    assert extract_financial_loss("I was defrauded of 2.5 lakhs in an IPO fraud") == 250000.0
    assert extract_financial_loss("Total stolen was 1.2 Crore across 3 accounts") == 12000000.0
    assert extract_financial_loss("Sent 50k for crypto mining") == 50000.0
    assert extract_financial_loss("Loss of Rs 3.5 Lac") == 350000.0

def test_empty_or_non_monetary_texts():
    assert extract_financial_loss("") is None
    assert extract_financial_loss(None) is None
    assert extract_financial_loss("The suspect called from mobile number +91 9876543210 and abused me.") is None
