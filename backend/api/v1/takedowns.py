from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.db.session import get_db
from domain.models.takedown import TakedownPolicy
from domain.agents.takedown_agent import TakedownAgent
from api.deps import get_current_user
from domain.models.user import User

router = APIRouter()

async def get_current_banker_or_admin(user: User = Depends(get_current_user)):
    if user.role not in ["admin", "banker", "police", "bank_employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized. Required role: banker or admin.")
    return user

@router.get("/pending")
async def get_pending_takedowns(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_banker_or_admin)):
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
async def approve_takedown(policy_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_banker_or_admin)):
    """Approve a policy and simulate the API call to NPCI/Telecom to freeze/block the asset."""
    result = await db.execute(select(TakedownPolicy).where(TakedownPolicy.id == policy_id))
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Takedown Policy not found")
        
    if policy.is_approved:
        raise HTTPException(status_code=400, detail="Policy already approved")
        
    policy.is_approved = True
    policy.approved_by = str(user.id)
    
    agent = TakedownAgent()
    receipt = await agent.execute_policy(policy)
    await agent.close()
    
    # Store receipt or metadata back into the policy if possible, or just log it
    # We will append the receipt to the reason to avoid db migration for now
    if "error" not in receipt:
        policy.reason += f" | Executed Ref: {receipt.get('npci_txn_ref') or receipt.get('service_request_id') or receipt.get('receipt')}"
        
    await db.commit()
    
    return {"message": f"Successfully executed action: {policy.action} on target: {policy.target}", "receipt": receipt}


@router.post("/trigger/{case_number}")
async def trigger_automated_takedown(
    case_number: str, 
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    Called by Investigators. Parses a case and automatically drafts AI-recommended takedown policies
    for all related hostile entities (UPI, phone numbers, URLs).
    These policies go into the pending queue for Bankers/Nodal officers to approve.
    """
    from domain.models.case import Case
    import uuid

    # 1. Fetch the case
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Draft mock takedown policies based on the case data for demonstration
    # In a real scenario, this would query Neo4j or Case evidence to find the exact entities
    policies_drafted = []
    
    # Draft UPI Freeze Policy
    upi_target = "suspect@okicici"
    p1 = TakedownPolicy(
        case_number=case_number,
        target=upi_target,
        target_type="upi",
        action="freeze_account",
        reason=f"Automated AI Draft: High confidence of scam in {case_number}. Freeze target UPI.",
    )
    db.add(p1)
    policies_drafted.append(upi_target)
    
    # Draft Phone Block Policy
    phone_target = "+919820041029" # Hardcoded suspect for the demo case
    p2 = TakedownPolicy(
        case_number=case_number,
        target=phone_target,
        target_type="phone",
        action="block_sim",
        reason=f"Automated AI Draft: Phone number extracted from {case_number} evidence.",
    )
    db.add(p2)
    policies_drafted.append(phone_target)
    
    await db.commit()

    return {
        "status": "success",
        "message": f"Automated RAIC Analysis complete. Drafted {len(policies_drafted)} takedown policies.",
        "policies_drafted": policies_drafted
    }
