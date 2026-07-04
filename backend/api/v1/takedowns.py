from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.db.session import get_db
from domain.models.takedown import TakedownPolicy
from core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_banker_or_admin(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    role = payload.get("role")
    if role not in ["admin", "banker", "police"]:
        raise HTTPException(status_code=403, detail="Unauthorized. Required role: banker or admin.")
    return payload

@router.get("/pending")
async def get_pending_takedowns(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_banker_or_admin)):
    """Fetch all takedown policies awaiting Banker/Nodal Officer approval."""
    result = await db.execute(select(TakedownPolicy).where(TakedownPolicy.is_approved == False))
    policies = result.scalars().all()
    
    return [
        {
            "id": p.id,
            "case_number": p.case_number,
            "target": p.target,
            "target_type": p.target_type,
            "action": p.action,
            "reason": p.reason,
            "created_at": p.created_at
        } for p in policies
    ]

@router.post("/{policy_id}/approve")
async def approve_takedown(policy_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_banker_or_admin)):
    """Approve a policy and simulate the API call to NPCI/Telecom to freeze/block the asset."""
    result = await db.execute(select(TakedownPolicy).where(TakedownPolicy.id == policy_id))
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Takedown Policy not found")
        
    if policy.is_approved:
        raise HTTPException(status_code=400, detail="Policy already approved")
        
    policy.is_approved = True
    policy.approved_by = user.get("sub")
    
    await db.commit()
    
    # In a real system, this would trigger an HTTP request to NPCI or Telecom Provider
    # e.g., await httpx.post("https://npci.mock.in/freeze", json={"upi_id": policy.target})
    
    return {"message": f"Successfully executed action: {policy.action} on target: {policy.target}"}
