import pytest
from datetime import datetime, timezone, timedelta
from transaction.feature_engine import FeatureEngine, haversine_km


def test_haversine_distance():
    # Delhi to Mumbai ~ 1150 km
    delhi_lat, delhi_lon = 28.6139, 77.2090
    mumbai_lat, mumbai_lon = 19.0760, 72.8777
    dist = haversine_km(delhi_lat, delhi_lon, mumbai_lat, mumbai_lon)
    assert 1100.0 < dist < 1200.0


def test_normal_transaction_features():
    engine = FeatureEngine()
    now = datetime(2026, 9, 13, 14, 30, tzinfo=timezone.utc)
    
    # User normally spends ₹500 - ₹2500
    history = [
        {"amount": 500.0, "timestamp": now - timedelta(days=5), "beneficiary_id": "friend@upi", "device_id": "DEV-1", "latitude": 28.6, "longitude": 77.2},
        {"amount": 1200.0, "timestamp": now - timedelta(days=3), "beneficiary_id": "store@upi", "device_id": "DEV-1", "latitude": 28.6, "longitude": 77.2},
        {"amount": 800.0, "timestamp": now - timedelta(days=1), "beneficiary_id": "friend@upi", "device_id": "DEV-1", "latitude": 28.6, "longitude": 77.2},
    ]

    current_txn = {
        "amount": 950.0,
        "timestamp": now,
        "account_id": "ACC-001",
        "beneficiary_id": "friend@upi",
        "device_id": "DEV-1",
        "latitude": 28.61,
        "longitude": 77.21
    }

    features = engine.compute_features(current_txn, account_history=history)

    assert features["is_new_beneficiary"] == 0.0
    assert features["is_new_device"] == 0.0
    assert features["is_unusual_hour"] == 0.0
    assert features["amount_anomaly_score"] < 0.20  # Well within normal low risk band (<20%)
    assert features["velocity_anomaly_score"] == 0.0
    assert features["distance_from_normal_km"] < 5.0


def test_account_takeover_anomaly_features():
    engine = FeatureEngine()
    # Midnight 02:30 AM
    now = datetime(2026, 9, 13, 2, 30, tzinfo=timezone.utc)
    
    history = [
        {"amount": 400.0, "timestamp": now - timedelta(days=4), "beneficiary_id": "mom@upi", "device_id": "DEV-LEGIT", "latitude": 19.07, "longitude": 72.87},
        {"amount": 1500.0, "timestamp": now - timedelta(days=2), "beneficiary_id": "groceries@upi", "device_id": "DEV-LEGIT", "latitude": 19.07, "longitude": 72.87},
    ]

    # Large spike to new mule beneficiary from unknown device in different city at 2:30 AM
    current_txn = {
        "amount": 85000.0,
        "timestamp": now,
        "account_id": "ACC-001",
        "beneficiary_id": "mule_gang@ybl",
        "device_id": "DEV-SUSPECT-99",
        "latitude": 28.61,  # Delhi (Mumbai to Delhi ~1150km)
        "longitude": 77.20
    }

    beneficiary_profile = {
        "risk_score": 0.90,
        "is_flagged": True,
        "first_received_at": now - timedelta(hours=3),
        "total_transactions": 2
    }

    device_profile = {
        "risk_score": 0.85,
        "is_emulator": True,
        "associated_accounts": ["ACC-001", "ACC-002", "ACC-003", "ACC-004"]
    }

    features = engine.compute_features(
        current_txn,
        account_history=history,
        beneficiary_profile=beneficiary_profile,
        device_profile=device_profile
    )

    assert features["is_new_beneficiary"] == 1.0
    assert features["is_new_device"] == 1.0
    assert features["is_unusual_hour"] == 1.0
    assert features["amount_anomaly_score"] > 0.8
    assert features["beneficiary_risk_score"] >= 0.9
    assert features["device_risk_score"] >= 0.85
    assert features["device_account_count"] == 4.0
    assert features["distance_from_normal_km"] > 1000.0
    assert features["location_anomaly_score"] == 1.0


def test_velocity_burst():
    engine = FeatureEngine()
    now = datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc)
    
    # 5 rapid transactions within the last 3 minutes
    history = [
        {"amount": 10000.0, "timestamp": now - timedelta(seconds=120), "beneficiary_id": "mule@upi"},
        {"amount": 10000.0, "timestamp": now - timedelta(seconds=90), "beneficiary_id": "mule@upi"},
        {"amount": 10000.0, "timestamp": now - timedelta(seconds=60), "beneficiary_id": "mule@upi"},
        {"amount": 10000.0, "timestamp": now - timedelta(seconds=30), "beneficiary_id": "mule@upi"},
    ]

    current_txn = {
        "amount": 15000.0,
        "timestamp": now,
        "account_id": "ACC-002",
        "beneficiary_id": "mule@upi"
    }

    features = engine.compute_features(current_txn, account_history=history)
    assert features["txns_last_1m"] >= 2.0
    assert features["txns_last_5m"] == 4.0
    assert features["velocity_anomaly_score"] >= 0.8

