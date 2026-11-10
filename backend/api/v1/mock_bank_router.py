import time
import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.deps import require_official_role
from domain.models.user import User
from services.mock_bank_service import mock_bank_service, SandboxScenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox/bank", tags=["Institutional Sandbox"])


class ScenarioConfigRequest(BaseModel):
    scenario: str = Field(..., description="SUCCESS | RATE_LIMITED_429 | SERVER_ERROR_500 | TIMEOUT_504 | CONNECTION_RESET | INVALID_AUTH | MALFORMED_RESPONSE | CONFLICTING_FINANCIAL | PARTIAL_FREEZE")
    bank_code: Optional[str] = Field(None, description="Optional bank code (e.g. SBIN, HDFC, ICIC). If omitted, sets default scenario.")


class SimulateCallbackRequest(BaseModel):
    bank_code: str = Field(..., description="Bank code sending callback (e.g. SBIN)")
    alert_reference: str = Field(..., description="Alert reference (e.g. DR-ALERT-2026-0001)")
    response_type: str = Field("ACKNOWLEDGEMENT", description="ACKNOWLEDGEMENT | INFO_REQUEST | ACTION_TAKEN | REJECTION")
    status_summary: str = Field("Debit freeze confirmed pursuant to Section 106 BNSS.")
    funds_frozen_amount: Optional[float] = None
    corrupt_signature: bool = Field(False, description="Simulate forged or corrupted signature")
    timestamp_skew_seconds: float = Field(0.0, description="Simulate clock skew in seconds (+/-)")


@router.post("/configure", response_model=Dict[str, Any])
async def configure_sandbox_scenario(
    payload: ScenarioConfigRequest,
    user: User = Depends(require_official_role)
):
    """
    Configures active simulation failure scenario for the mock banking adapter.
    Enables developers and partner QA teams to test resilience against partner bank downtime.
    """
    valid_scenarios = {
        SandboxScenario.SUCCESS,
        SandboxScenario.DELAYED_ACK,
        SandboxScenario.RATE_LIMITED_429,
        SandboxScenario.SERVER_ERROR_500,
        SandboxScenario.TIMEOUT_504,
        SandboxScenario.CONNECTION_RESET,
        SandboxScenario.INVALID_AUTH,
        SandboxScenario.MALFORMED_RESPONSE,
        SandboxScenario.CONFLICTING_FINANCIAL,
        SandboxScenario.PARTIAL_FREEZE
    }
    if payload.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{payload.scenario}'. Valid options: {sorted(list(valid_scenarios))}"
        )

    mock_bank_service.set_scenario(payload.scenario, bank_code=payload.bank_code)
    logger.info(f"Sandbox scenario set to {payload.scenario} (bank: {payload.bank_code or 'ALL'}) by {user.email}")

    return {
        "status": "CONFIGURED",
        "scenario": payload.scenario,
        "bank_code": payload.bank_code or "ALL",
        "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX"
    }


@router.get("/idempotency-store", response_model=Dict[str, Any])
async def get_sandbox_idempotency_store(
    user: User = Depends(require_official_role)
):
    """
    Inspects the receiver-side mock bank idempotency store.
    Proves that retried dispatches retain identical idempotency keys and return cached acknowledgements.
    """
    return {
        "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX",
        "store": mock_bank_service.get_idempotency_store_dump()
    }


@router.post("/reset", response_model=Dict[str, Any])
async def reset_sandbox_store(
    user: User = Depends(require_official_role)
):
    """
    Resets the mock bank's receiver-side cache and scenarios back to default.
    """
    mock_bank_service.reset()
    return {
        "status": "RESET_COMPLETED",
        "institution_mode": "SIMULATED_INSTITUTIONAL_SANDBOX"
    }


@router.post("/simulate-callback", response_model=Dict[str, Any])
async def generate_simulated_callback(
    payload: SimulateCallbackRequest,
    user: User = Depends(require_official_role)
):
    """
    Generates a cryptographically signed mock bank callback payload
    ready to be delivered to `/api/v1/bank-integrations/{bank_code}/callback`.
    """
    cb_payload = {
        "alert_reference": payload.alert_reference,
        "bank_reference_number": f"CB-{payload.bank_code}-{uuid.uuid4().hex[:8].upper()}",
        "response_type": payload.response_type,
        "status_summary": payload.status_summary,
        "funds_frozen_amount": payload.funds_frozen_amount,
        "details": {
            "source": "SIMULATED_BANK_CALLBACK",
            "bank_code": payload.bank_code,
            "disclaimer": "Simulated institutional response under BSA 2023 testing provisions."
        }
    }

    nonce = f"NONCE-{uuid.uuid4().hex[:12].upper()}"
    ts = str(time.time() + payload.timestamp_skew_seconds)

    raw_sig = mock_bank_service.sign_payload(cb_payload)
    sig = "CORRUPTED_HMAC_DIGEST_FORGED" if payload.corrupt_signature else raw_sig

    return {
        "callback_url": f"/api/v1/bank-integrations/{payload.bank_code}/callback",
        "headers": {
            "X-Bank-Signature": sig,
            "X-Bank-Timestamp": ts,
            "X-Bank-Nonce": nonce
        },
        "payload": cb_payload
    }
