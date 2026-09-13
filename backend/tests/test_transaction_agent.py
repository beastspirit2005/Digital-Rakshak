import pytest
import asyncio
from datetime import datetime, timezone
from domain.agents.transaction_agent import TransactionAgent
from domain.models.transaction import FrictionAction, RiskBand


@pytest.mark.asyncio
async def test_transaction_agent_normal_payment():
    agent = TransactionAgent()
    now = datetime(2026, 9, 13, 11, 0, tzinfo=timezone.utc)

    txn = {
        "transaction_id": "TXN-TEST-NORMAL",
        "account_id": "ACC-5510",
        "beneficiary_id": "local_shop@upi",
        "device_id": "DEV-MY-PHONE",
        "amount": 450.0,
        "channel": "UPI",
        "timestamp": now
    }

    # Pass mock account history
    history = [
        {"amount": 500.0, "timestamp": now, "beneficiary_id": "local_shop@upi", "device_id": "DEV-MY-PHONE"},
        {"amount": 600.0, "timestamp": now, "beneficiary_id": "other@upi", "device_id": "DEV-MY-PHONE"},
    ]

    res = await agent.analyze_transaction(current_txn=txn, account_history=history, graph_risk_override=0.0)

    assert res["transaction_id"] == "TXN-TEST-NORMAL"
    assert res["decision"] == FrictionAction.APPROVE.value
    assert res["risk_band"] == RiskBand.LOW.value
    assert res["risk_score"] < 0.20
    assert len(res["signals"]) == 7
    assert any(s["name"] == "amount_anomaly" for s in res["signals"])


@pytest.mark.asyncio
async def test_transaction_agent_fraud_attack():
    agent = TransactionAgent()
    now = datetime(2026, 9, 13, 3, 15, tzinfo=timezone.utc)  # 03:15 AM

    # Large drain to new mule account from unknown device
    txn = {
        "transaction_id": "TXN-TEST-FRAUD",
        "account_id": "ACC-VICTIM-99",
        "beneficiary_id": "syndicate_mule@ybl",
        "device_id": "DEV-ATTACKER-PHONE",
        "amount": 92000.0,
        "channel": "UPI",
        "timestamp": now
    }

    # History: normal transfer to family, then micro-probe transfer 5 mins ago
    history = [
        {"amount": 500.0, "timestamp": now, "beneficiary_id": "family@upi", "device_id": "DEV-MY-PHONE"},
        {"amount": 100.0, "timestamp": now, "beneficiary_id": "syndicate_mule@ybl", "device_id": "DEV-ATTACKER-PHONE"},
    ]

    device_profile = {
        "device_id": "DEV-ATTACKER-PHONE",
        "is_emulator": True,
        "associated_accounts": ["ACC-1", "ACC-2", "ACC-3", "ACC-VICTIM-99"],
        "risk_score": 0.90
    }

    beneficiary_profile = {
        "beneficiary_id": "syndicate_mule@ybl",
        "is_flagged": True,
        "risk_score": 0.95,
        "first_received_at": now
    }

    res = await agent.analyze_transaction(
        current_txn=txn,
        account_history=history,
        device_profile=device_profile,
        beneficiary_profile=beneficiary_profile,
        graph_risk_override=0.90  # Simulating multi-account graph cluster match
    )

    assert res["decision"] == FrictionAction.HOLD_AND_INVESTIGATE.value
    assert res["risk_band"] == RiskBand.CRITICAL.value
    assert res["risk_score"] >= 0.88
    assert "SHARED_DEVICE_RING" in res["reason_codes"]
    assert "MULE_BENEFICIARY" in res["reason_codes"]
    assert res["attack_dna"]["matched"] is True

