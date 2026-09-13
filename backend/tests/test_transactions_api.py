import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
import uuid

from main import app
from domain.models.transaction import FrictionAction, RiskBand, TransactionStatus
from infrastructure.db.session import engine


@pytest.mark.asyncio
async def test_api_ingest_normal_transaction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "transaction_id": f"TXN-NORM-{uuid.uuid4().hex[:6].upper()}",
            "account_id": "ACC-TEST-USER-1",
            "beneficiary_id": "grocery_store@upi",
            "device_id": "DEV-USER-PHONE-1",
            "amount": 350.0,
            "currency": "INR",
            "transaction_type": "UPI",
            "channel": "UPI",
            "city": "Mumbai",
            "state": "Maharashtra"
        }

        response = await ac.post("/v1/transactions/", json=payload)
        assert response.status_code == 201, f"Response: {response.text}"
        data = response.json()

        assert data["transaction_id"] == payload["transaction_id"]
        assert data["decision"] == FrictionAction.APPROVE.value
        assert data["risk_band"] == RiskBand.LOW.value
        assert data["status"] == TransactionStatus.APPROVED.value
        assert data["risk_score"] < 0.25

    await engine.dispose()


@pytest.mark.asyncio
async def test_api_ingest_and_review_fraud_transaction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        txn_code = f"TXN-FRAUD-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "transaction_id": txn_code,
            "account_id": "ACC-TEST-VICTIM-99",
            "beneficiary_id": "syndicate_mule_account@ybl",
            "device_id": "DEV-SUSPICIOUS-EMU-1",
            "amount": 95000.0,
            "currency": "INR",
            "transaction_type": "UPI",
            "channel": "UPI",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_metadata": {
                "device_profile": {
                    "device_id": "DEV-SUSPICIOUS-EMU-1",
                    "is_emulator": True,
                    "associated_accounts": ["ACC-1", "ACC-2", "ACC-3", "ACC-TEST-VICTIM-99"],
                    "risk_score": 0.90
                },
                "beneficiary_profile": {
                    "beneficiary_id": "syndicate_mule_account@ybl",
                    "is_flagged": True,
                    "risk_score": 0.95
                },
                "graph_risk": 0.90
            }
        }

        # 1. Ingest
        response = await ac.post("/v1/transactions/", json=payload)
        assert response.status_code == 201, f"Response: {response.text}"
        data = response.json()

        assert data["transaction_id"] == txn_code
        assert data["risk_score"] >= 0.50
        assert data["status"] in [TransactionStatus.HELD.value, TransactionStatus.STEP_UP_REQUIRED.value]
        txn_db_id = data["id"]

        # 2. Query Risk
        risk_resp = await ac.get(f"/v1/transactions/{txn_code}/risk")
        assert risk_resp.status_code == 200
        risk_data = risk_resp.json()
        assert risk_data["transaction_id"] == txn_code
        assert "amount" in risk_data["sub_scores"]

        # 3. Query Explanation
        exp_resp = await ac.get(f"/v1/transactions/{txn_code}/explanation")
        assert exp_resp.status_code == 200
        exp_data = exp_resp.json()
        assert exp_data["decision"] in [FrictionAction.TEMPORARY_HOLD.value, FrictionAction.HOLD_AND_INVESTIGATE.value, FrictionAction.STEP_UP_VERIFICATION.value]
        assert len(exp_data["reason_codes"]) > 0

        # 4. Risk Feed
        feed_resp = await ac.get("/v1/transactions/risk-feed?account_id=ACC-TEST-VICTIM-99")
        assert feed_resp.status_code == 200
        feed_data = feed_resp.json()
        assert feed_data["total"] >= 1
        assert any(item["transaction_id"] == txn_code for item in feed_data["items"])

        # 5. Campaigns
        camp_resp = await ac.get("/v1/transactions/campaigns")
        assert camp_resp.status_code == 200
        assert "campaigns" in camp_resp.json()

        # 6. Account Risk Network (Neo4j / fallback)
        net_resp = await ac.get("/v1/transactions/accounts/ACC-TEST-VICTIM-99/risk-network")
        assert net_resp.status_code == 200
        net_data = net_resp.json()
        assert "nodes" in net_data
        assert "edges" in net_data

    await engine.dispose()
