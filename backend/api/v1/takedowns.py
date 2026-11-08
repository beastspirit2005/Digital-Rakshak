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
    from domain.models.bank import FinancialTransaction
    import uuid
    import logging

    logger = logging.getLogger(__name__)

    # 1. Fetch the case
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Extract real hostile entities from case evidence and AI decision object
    upi_pattern = re.compile(r"[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+")
    phone_pattern = re.compile(r"(?:\+91|91|0)?[6-9]\d{9}")
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
        entities_data = ai_dec.get("entities", {})
        if isinstance(entities_data, dict):
            for k, val_list in entities_data.items():
                if isinstance(val_list, list):
                    for v in val_list:
                        v_str = str(v).strip()
                        if not v_str:
                            continue
                        if k.upper() == "UPI" and "@" in v_str:
                            candidate_upis.add(v_str)
                        elif k.upper() == "PHONE":
                            candidate_phones.add(v_str)
                        elif k.upper() in ["URLS", "URL"]:
                            candidate_urls.add(v_str)
                        else:
                            _extract_from_text(v_str)
                elif isinstance(val_list, str):
                    _extract_from_text(val_list)
        elif isinstance(entities_data, list):
            for entity in entities_data:
                _extract_from_text(str(entity))

        for ev in ai_dec.get("evidence", []):
            _extract_from_text(str(ev))

    # Scan linked financial transactions
    try:
        txn_result = await db.execute(
            select(FinancialTransaction).where(FinancialTransaction.case_id == case.id).limit(20)
        )
        for txn in txn_result.scalars().all():
            if txn.beneficiary_vpa:
                candidate_upis.add(txn.beneficiary_vpa.strip())
    except Exception as txn_err:
        await db.rollback()
        logger.warning(f"Note on financial transactions scan for takedown: {txn_err}")

    filtered_upis = [u for u in candidate_upis if "@" in u][:5]
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

    # Deduplicate against existing policies
    existing_targets = set()
    try:
        existing_res = await db.execute(
            select(TakedownPolicy.target).where(TakedownPolicy.case_number == case_number)
        )
        existing_targets = set(existing_res.scalars().all())
    except Exception as ex_err:
        await db.rollback()
        logger.warning(f"Note querying existing takedown targets: {ex_err}")

    policies_drafted = []

    for upi in filtered_upis:
        if upi not in existing_targets:
            p = TakedownPolicy(
                case_number=case_number,
                target=upi,
                target_type="upi",
                action="freeze_account",
                reason=f"AI Entity Extraction: UPI ID {upi} linked to fraud incident {case_number}.",
            )
            db.add(p)
            existing_targets.add(upi)
        policies_drafted.append(upi)

    for phone in filtered_phones:
        if phone not in existing_targets:
            p = TakedownPolicy(
                case_number=case_number,
                target=phone,
                target_type="phone",
                action="block_sim",
                reason=f"AI Entity Extraction: Phone number {phone} extracted from {case_number} evidence.",
            )
            db.add(p)
            existing_targets.add(phone)
        policies_drafted.append(phone)

    for url in filtered_urls:
        if url not in existing_targets:
            p = TakedownPolicy(
                case_number=case_number,
                target=url,
                target_type="url",
                action="block_domain",
                reason=f"AI Entity Extraction: Phishing/fraud URL {url} found in {case_number} evidence.",
            )
            db.add(p)
            existing_targets.add(url)
        policies_drafted.append(url)

    try:
        await db.commit()
    except Exception as commit_err:
        await db.rollback()
        logger.error(f"Error persisting takedown policies: {commit_err}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to persist drafted takedown policies")

    return {
        "status": "success",
        "message": f"Dynamic RAIC Analysis complete. Drafted {len(policies_drafted)} takedown policies from real case entities.",
        "policies_drafted": policies_drafted,
    }
