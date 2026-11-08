import pytest
import uuid
from domain.services.transaction_extractor import (
    extract_transaction_intelligence,
    mask_account_number,
    ExtractedTransactionIntelligence
)
from domain.services.bank_registry_service import (
    INITIAL_VERIFIED_BANKS,
    VPA_HANDLE_TO_BANK_CODE
)


def test_mask_account_number():
    assert mask_account_number("123456789012") == "********9012"
    assert mask_account_number("987654321") == "*****4321"
    assert mask_account_number("1234") == "****1234"


def test_extract_upi_complaint_with_vpa_and_utr():
    complaint = (
        "I was scammed by a fake electricity bill caller. They asked me to transfer ₹45,000 "
        "to fraudster@okhdfcbank using Google Pay. The UTR number is 987654321012. "
        "The money was deducted from my account."
    )
    intel = extract_transaction_intelligence(complaint)
    
    assert intel.amount == 45000.0
    assert intel.transaction_reference == "987654321012"
    assert intel.beneficiary_vpa == "fraudster@okhdfcbank"
    assert intel.payment_rail == "UPI"
    assert intel.confidence_score >= 0.70
    assert intel.verification_status == "RESOLVED_INFERRED"


def test_extract_imps_with_ifsc_and_account():
    complaint = (
        "Transferred INR 1,25,000 via IMPS to account 912345678901 at Axis Bank IFSC UTIB0001234. "
        "Reference No: 456789012345. Suspect claimed to be CBI officer."
    )
    intel = extract_transaction_intelligence(complaint)

    assert intel.amount == 125000.0
    assert intel.transaction_reference == "456789012345"
    assert intel.beneficiary_ifsc == "UTIB0001234"
    assert intel.beneficiary_account_masked == "********8901"
    assert intel.payment_rail == "IMPS"
    assert intel.confidence_score >= 0.70


def test_extract_dual_ifsc_remitter_and_beneficiary():
    complaint = (
        "Debited from my SBI account IFSC SBIN0001234 to beneficiary ICICI account IFSC ICIC0005678. "
        "Lost Rs. 50,000 in fake stock investment scheme. UTR: 112233445566."
    )
    intel = extract_transaction_intelligence(complaint)

    assert intel.amount == 50000.0
    assert intel.remitter_ifsc == "SBIN0001234"
    assert intel.beneficiary_ifsc == "ICIC0005678"
    assert intel.transaction_reference == "112233445566"
    assert intel.confidence_score >= 0.80


def test_extract_minimal_or_empty_complaint():
    complaint = "Someone called me and was rude."
    intel = extract_transaction_intelligence(complaint)
    
    assert intel.amount is None
    assert intel.transaction_reference is None
    assert intel.beneficiary_vpa is None
    assert intel.beneficiary_ifsc is None
    assert intel.confidence_score <= 0.35
    assert intel.verification_status == "EXTRACTED_UNVERIFIED"


def test_vpa_mapping_sanity():
    assert VPA_HANDLE_TO_BANK_CODE["okhdfcbank"] == "HDFC"
    assert VPA_HANDLE_TO_BANK_CODE["oksbi"] == "SBIN"
    assert VPA_HANDLE_TO_BANK_CODE["okaxis"] == "AXIS"
    assert VPA_HANDLE_TO_BANK_CODE["ybl"] == "YESB"
    assert VPA_HANDLE_TO_BANK_CODE["paytm"] == "PYTM"


def test_verified_banks_directory_structure():
    assert len(INITIAL_VERIFIED_BANKS) >= 15
    for b in INITIAL_VERIFIED_BANKS:
        assert "bank_code" in b
        assert "bank_name" in b
        assert "ifsc_prefix" in b
        assert "supported_rails" in b
        assert len(b["ifsc_prefix"]) == 4
