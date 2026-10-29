import pytest
from domain.services.financial_loss_extractor import extract_financial_loss

def test_financial_loss_extraction_from_real_scam_samples():
    # Sample from Bank Switch Escalation
    sample1 = (
        "Bank Switch Escalation: Flagged Transaction TXN-FRAUD-E27C6E. "
        "Remitter Account ACC-TEST-VICTIM transferred INR 95,000.00 to Beneficiary ACC-TEST-MULE. "
        "Reason: Sudden High-Value Transfer."
    )
    assert extract_financial_loss(sample1) == 95000.0

    # Sample from citizen complaint with ₹
    sample2 = "I was promised part time job on telegram and transferred ₹25,000 via phonepe"
    assert extract_financial_loss(sample2) == 25000.0

    # Sample with lakhs
    sample3 = "Fake customs officer threatened me and I paid 4.5 lakhs into mule account"
    assert extract_financial_loss(sample3) == 450000.0

    # Sample with crores
    sample4 = "Trading app scam lost 1.5 Crore total over 2 weeks"
    assert extract_financial_loss(sample4) == 15000000.0

    # Fallback when no amount
    sample5 = "Unknown caller claimed to be police officer and harassed me."
    assert extract_financial_loss(sample5) is None
