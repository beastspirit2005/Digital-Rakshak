import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user, OFFICIAL_INSTITUTIONAL_ROLES
from domain.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

class FreezeRequest(BaseModel):
    target_id: str
    reason: str

class BlockRequest(BaseModel):
    phone_number: str
    reason: str

def _require_official_access(user: User):
    if user.role not in OFFICIAL_INSTITUTIONAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Official law enforcement or nodal officer credentials required."
        )

@router.post("/npci/freeze-upi")
async def mock_npci_freeze(req: FreezeRequest, user: User = Depends(get_current_user)):
    """
    Mock NPCI endpoint to simulate freezing a UPI ID or Bank Account.
    """
    _require_official_access(user)
    logger.info(f"[NPCI MOCK] Received request to freeze: {req.target_id} from {user.email}")
    # Async delay without blocking event loop
    await asyncio.sleep(0.5)
    
    return {
        "status": "success",
        "action_taken": "ACCOUNT_FROZEN",
        "target": req.target_id,
        "npci_txn_ref": f"NPCI-{uuid.uuid4().hex[:12].upper()}",
        "timestamp": time.time()
    }

@router.post("/telecom/block-sim")
async def mock_telecom_block(req: BlockRequest, user: User = Depends(get_current_user)):
    """
    Mock Telecom endpoint to simulate blocking a phone number.
    """
    _require_official_access(user)
    logger.info(f"[TELECOM MOCK] Received request to block: {req.phone_number} from {user.email}")
    # Async delay without blocking event loop
    await asyncio.sleep(0.5)
    
    return {
        "status": "success",
        "action_taken": "SIM_BLOCKED",
        "target": req.phone_number,
        "service_request_id": f"SR-{uuid.uuid4().hex[:10].upper()}",
        "timestamp": time.time()
    }
