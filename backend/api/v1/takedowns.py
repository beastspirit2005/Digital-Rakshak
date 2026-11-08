import re
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
    Called by Investigators. Dynamically extracts hostile entities (UPI, phone numbers, URLs)
    from real case evidence and creates takedown policies for Banker/Nodal Officer approval.
    """
    if user.role not in ["admin", "police", "cyber_cell", "banker", "bank_employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized. Authorized official role required to draft takedown policies.")

    from domain.models.case import Case
    from domain.models.transaction import Transaction
    import uuid

    # 1. Fetch the case
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Extract real hostile entities from case evidence and AI decision object
    upi_pattern = re.compile(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+')
    phone_pattern = re.compile(r'(?:\+91|91|0)?[6-9]\d{9}')
    url_pattern = re.compile(r'https?://[^\s\'\"<>]+')

    candidate_upis: set = set()
    candidate_phones: set = set()
    candidate_urls: set = set()

    def _extract_from_text(text: str):
        if not text:
            return
        candidate_upis.update(upi_pattern.findall(text))
        candidate_phones.update(phone_pattern.findall(text))
        candidate_urls.update(url_pattern.findall(text))

    _extract_from_text(case.scam_text or "")
    _extract_from_text(case.triage_notes or "")

    ai_dec = case.ai_decision or {}
    if isinstance(ai_dec, dict):
        for entity in ai_dec.get("entities", []):
            _extract_from_text(str(entity))
        for ev in ai_dec.get("evidence", []):
            _extract_from_text(str(ev))

    # Scan linked financial transactions
    txn_result = await db.execute(
        select(Transaction).where(Transaction.case_id == case.id).limit(20)
    )
    for txn in txn_result.scalars().all():
        if txn.beneficiary_id:
            if "@" in txn.beneficiary_id:
                candidate_upis.add(txn.beneficiary_id)
            elif re.match(r"^[6-9]\d{9}$", txn.beneficiary_id):
                candidate_phones.add(txn.beneficiary_id)

    _legit_domains = {"sbi", "icici", "hdfc", "axis", "pnb", "kotak", "upi", "razorpay", "paytm", "googlepay", "phonep"}
    filtered_upis = [u for u in candidate_upis if u.split("@")[-1].lower() not in _legit_domains][:5]
    filtered_phones = list(candidate_phones)[:5]
    filtered_urls = [u for u in candidate_urls if "digitalrakshak" not in u.lower()][:3]

    if not filtered_upis and not filtered_phones and not filtered_urls:
        return {
            "status": "no_entities_found",
            "message": (
                f"No hostile UPI IDs, phone numbers, or URLs could be extracted from case {case_number}. "
                "Please verify the case evidence contains sufficient transaction or contact data."
            ),
            "policies_drafted": [],
        }

    policies_drafted = []

    for upi in filtered_upis:
        p = TakedownPolicy(
            case_number=case_number,
            target=upi,
            target_type="upi",
            action="freeze_account",
            reason=f"AI Entity Extraction: UPI ID {upi} linked to fraud incident {case_number}.",
        )
        db.add(p)
        policies_drafted.append(upi)

    for phone in filtered_phones:
        p = TakedownPolicy(
            case_number=case_number,
            target=phone,
            target_type="phone",
            action="block_sim",
            reason=f"AI Entity Extraction: Phone number {phone} extracted from {case_number} evidence.",
        )
        db.add(p)
        policies_drafted.append(phone)

    for url in filtered_urls:
        p = TakedownPolicy(
            case_number=case_number,
            target=url,
            target_type="url",
            action="block_domain",
            reason=f"AI Entity Extraction: Phishing/fraud URL {url} found in {case_number} evidence.",
        )
        db.add(p)
        policies_drafted.append(url)

    await db.commit()

    return {
        "status": "success",
        "message": f"Dynamic RAIC Analysis complete. Drafted {len(policies_drafted)} takedown policies from real case entities.",
        "policies_drafted": policies_drafted,
    }
