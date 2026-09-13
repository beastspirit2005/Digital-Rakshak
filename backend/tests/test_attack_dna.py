import pytest
from datetime import datetime, timezone, timedelta
from transaction.attack_dna import AttackDNAMatcher


def test_attack_dna_account_takeover_match():
    matcher = AttackDNAMatcher()
    now = datetime(2026, 9, 13, 2, 45, tzinfo=timezone.utc)

    # History: 10 mins ago, user had a micro-probe test transfer of ₹100
    history = [
        {"amount": 100.0, "timestamp": now - timedelta(minutes=10), "beneficiary_id": "mule@upi"},
    ]

    # Current txn: large ₹75,000 transfer from new device to new beneficiary
    current_txn = {
        "amount": 75000.0,
        "timestamp": now,
        "account_id": "ACC-991",
        "beneficiary_id": "mule@upi",
        "device_id": "DEV-NEW"
    }

    features = {
        "is_new_device": 1.0,
        "is_new_beneficiary": 1.0,
        "is_unusual_hour": 1.0,
        "amount_anomaly_score": 0.90
    }

    result = matcher.evaluate(current_txn, features, account_history=history)

    assert result["matched"] is True
    assert result["dna_id"] in ["DNA-UPI-ACCOUNT-TAKEOVER-V1", "DNA-NIGHT-SIPHON-V1"]
    assert result["similarity"] >= 0.75
    assert "NEW_DEVICE" in result["matched_steps"]
    assert "LARGE_TRANSFER" in result["matched_steps"]


def test_attack_dna_normal_no_match():
    matcher = AttackDNAMatcher()
    now = datetime(2026, 9, 13, 14, 0, tzinfo=timezone.utc)

    history = [
        {"amount": 500.0, "timestamp": now - timedelta(days=2), "beneficiary_id": "store@upi"},
    ]

    current_txn = {
        "amount": 1200.0,
        "timestamp": now,
        "account_id": "ACC-991",
        "beneficiary_id": "store@upi",
        "device_id": "DEV-KNOWN"
    }

    features = {
        "is_new_device": 0.0,
        "is_new_beneficiary": 0.0,
        "is_unusual_hour": 0.0,
        "amount_anomaly_score": 0.0
    }

    result = matcher.evaluate(current_txn, features, account_history=history)
    assert result["matched"] is False
    assert result["similarity"] < 0.50

