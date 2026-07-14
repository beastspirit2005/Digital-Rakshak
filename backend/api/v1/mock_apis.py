from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class FreezeRequest(BaseModel):
    target_id: str
    reason: str

class BlockRequest(BaseModel):
    phone_number: str
    reason: str

@router.post("/npci/freeze-upi")
async def mock_npci_freeze(req: FreezeRequest):
    """
    Mock NPCI endpoint to simulate freezing a UPI ID or Bank Account.
    """
    logger.info(f"[NPCI MOCK] Received request to freeze: {req.target_id}")
    # Simulate network delay
    time.sleep(0.5)
    
    return {
        "status": "success",
        "action_taken": "ACCOUNT_FROZEN",
        "target": req.target_id,
        "npci_txn_ref": f"NPCI-{uuid.uuid4().hex[:12].upper()}",
        "timestamp": time.time()
    }

@router.post("/telecom/block-sim")
async def mock_telecom_block(req: BlockRequest):
    """
    Mock Telecom endpoint to simulate blocking a phone number.
    """
    logger.info(f"[TELECOM MOCK] Received request to block: {req.phone_number}")
    # Simulate network delay
    time.sleep(0.5)
    
    return {
        "status": "success",
        "action_taken": "SIM_BLOCKED",
        "target": req.phone_number,
        "service_request_id": f"SR-{uuid.uuid4().hex[:10].upper()}",
        "timestamp": time.time()
    }
