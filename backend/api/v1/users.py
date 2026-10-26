from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import secrets
import string

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_welcome_email, send_account_created_email, send_account_deleted_email
from domain.models.user import User
from domain.models.audit_event import AuditEvent
from core.security import decode_access_token, get_password_hash
from api.deps import get_current_admin, get_current_user, OFFICIAL_INSTITUTIONAL_ROLES

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    role: str

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

router = APIRouter()

@router.get("/")
@router.get("")
@limiter.limit("60/minute")
async def get_users(request: Request, skip: int = 0, limit: int = 50, full_name: Optional[str] = None, email: Optional[str] = None, role: Optional[str] = None, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    """List all users (Admin only)"""
    limit = min(max(1, limit), 100)
    query = select(User)
    if full_name:
        escaped_name = full_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(User.full_name.ilike(f"%{escaped_name}%"))
    if email:
        escaped_email = email.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(User.email.ilike(f"%{escaped_email}%"))
    if role:
        query = query.where(User.role == role)
        
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_approved": user.is_approved,
            "created_at": user.created_at
        } for user in users
    ]

class ConsentUpdate(BaseModel):
    ai_threat_analysis: Optional[bool] = None
    telemetry_monitoring: Optional[bool] = None
    syndicate_intel_sharing: Optional[bool] = None
    communication_alerts: Optional[bool] = None

_user_consents = {}

@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get the current logged-in user profile with plan entitlements"""
    is_user_pro = (
        user.role in OFFICIAL_INSTITUTIONAL_ROLES
        or (
            getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
            and getattr(user, "b2c_subscription_status", "") == "active"
        )
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
        "b2c_plan_code": getattr(user, "b2c_plan_code", "b2c_free") or "b2c_free",
        "b2c_subscription_status": getattr(user, "b2c_subscription_status", "active") or "active",
        "is_pro": is_user_pro,
        "created_at": user.created_at
    }


@router.get("/me/consent")
async def get_my_consent(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns active consent preferences in accordance with DPDP Act 2023.
    Persisted immutably in the database AuditEvent log.
    """
    from datetime import datetime, timezone
    uid = str(user.id)
    
    stored = _user_consents.get(uid)
    if not stored:
        res = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.actor_id == user.id, AuditEvent.action == "DPDP_CONSENT_UPDATED")
            .order_by(AuditEvent.timestamp.desc())
            .limit(1)
        )
        latest_audit = res.scalar_one_or_none()
        if latest_audit and latest_audit.metadata_json:
            stored = latest_audit.metadata_json
            _user_consents[uid] = stored
            
    if not stored:
        stored = {
            "ai_threat_analysis": True,
            "telemetry_monitoring": True,
            "syndicate_intel_sharing": True,
            "communication_alerts": True,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        _user_consents[uid] = stored

    return {
        "user_id": uid,
        "dpdp_act_compliant": True,
        "notice": "Under India's Digital Personal Data Protection Act 2023, you have the right to withdraw consent at any time for non-essential processing purposes.",
        "consents": stored
    }


@router.post("/me/consent")
async def update_my_consent(data: ConsentUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Updates or revokes specific data processing consents under DPDP Act 2023.
    Persisted to database via AuditEvent and cached locally.
    """
    from datetime import datetime, timezone
    uid = str(user.id)
    
    current = _user_consents.get(uid)
    if not current:
        res = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.actor_id == user.id, AuditEvent.action == "DPDP_CONSENT_UPDATED")
            .order_by(AuditEvent.timestamp.desc())
            .limit(1)
        )
        latest_audit = res.scalar_one_or_none()
        if latest_audit and latest_audit.metadata_json:
            current = dict(latest_audit.metadata_json)
        else:
            current = {
                "ai_threat_analysis": True,
                "telemetry_monitoring": True,
                "syndicate_intel_sharing": True,
                "communication_alerts": True
            }

    if data.ai_threat_analysis is not None:
        current["ai_threat_analysis"] = data.ai_threat_analysis
    if data.telemetry_monitoring is not None:
        current["telemetry_monitoring"] = data.telemetry_monitoring
    if data.syndicate_intel_sharing is not None:
        current["syndicate_intel_sharing"] = data.syndicate_intel_sharing
    if data.communication_alerts is not None:
        current["communication_alerts"] = data.communication_alerts
    current["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    _user_consents[uid] = current
    
    # Persist immutable audit log entry to database
    audit_log = AuditEvent(
        actor_id=user.id,
        actor_role=user.role,
        action="DPDP_CONSENT_UPDATED",
        resource_type="user",
        resource_id=uid,
        metadata_json=current
    )
    db.add(audit_log)
    await db.commit()

    return {
        "status": "success",
        "message": "Consent preferences updated successfully under DPDP Act 2023.",
        "consents": current
    }


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.patch("/me")
async def update_my_profile(
    data: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Allows a citizen to update their display name or registered email address.
    """
    if data.full_name is not None and data.full_name.strip():
        user.full_name = data.full_name.strip()

    if data.email is not None and data.email.strip():
        new_email = data.email.strip().lower()
        if new_email != user.email:
            existing = await db.execute(select(User).where(User.email == new_email, User.id != user.id))
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="This email is already in use by another account.")
            user.email = new_email

    await db.commit()
    await db.refresh(user)

    is_user_pro = (
        user.role in OFFICIAL_INSTITUTIONAL_ROLES
        or (
            getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
            and getattr(user, "b2c_subscription_status", "") == "active"
        )
    )

    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "b2c_plan_code": getattr(user, "b2c_plan_code", "b2c_free") or "b2c_free",
            "b2c_subscription_status": getattr(user, "b2c_subscription_status", "active") or "active",
            "is_pro": is_user_pro,
        }
    }


@router.delete("/me")
async def delete_my_account(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Self-serve account erasure under DPDP Act 2023 Section 12 (Right to Erasure).
    Permanently wipes the user's account, nullifies foreign keys, and purges scan history.
    """
    user_id = str(user.id)
    email = user.email

    from sqlalchemy import update
    from domain.models.case import Case
    from domain.models.evidence import Evidence
    from domain.models.help_message import HelpMessage
    from domain.models.support import SupportTicket
    from domain.models.takedown import TakedownPolicy

    await db.execute(update(Case).where(Case.submitted_by == user_id).values(submitted_by=None))
    await db.execute(update(Case).where(Case.assigned_to == user_id).values(assigned_to=None))
    await db.execute(update(Evidence).where(Evidence.evidence_owner == user_id).values(evidence_owner=None))
    await db.execute(update(HelpMessage).where(HelpMessage.user_id == user_id).values(user_id=None))
    await db.execute(update(SupportTicket).where(SupportTicket.user_id == user_id).values(user_id=None))
    await db.execute(update(TakedownPolicy).where(TakedownPolicy.approved_by == user_id).values(approved_by=None))

    from api.v1.scan import _mem_user_scans
    if user_id in _mem_user_scans:
        del _mem_user_scans[user_id]

    if user_id in _user_consents:
        del _user_consents[user_id]

    await db.delete(user)
    await db.commit()

    return {
        "status": "success",
        "message": f"Account for {email} and all associated personal data have been permanently erased."
    }


@router.get("/pending")
async def get_pending_users(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    """List unapproved users (Admin only)"""
    result = await db.execute(select(User).where(User.is_approved == False))
    users = result.scalars().all()
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_approved": user.is_approved,
            "created_at": user.created_at
        } for user in users
    ]

@router.post("/{user_id}/approve")
async def approve_user(user_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_approved = True
    await db.commit()
    
    # Send welcome email now that they are approved
    email_sent = False
    try:
        email_sent = await send_welcome_email(user.email, user.full_name, user.role)
    except Exception as e:
        print(f"Failed to send welcome email to {user.email}: {e}")
    
    return {
        "message": f"User {user.email} has been approved.",
        "email_sent": email_sent
    }

def generate_secure_password(length=12):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Guarantee at least one of each required group
    pwd = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill the rest of the password length
    alphabet = lowercase + uppercase + digits + special
    pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
    
    # Cryptographically shuffle the characters to avoid a predictable position pattern
    shuffled_pwd = sorted(pwd, key=lambda x: secrets.randbelow(10000))
    
    return ''.join(shuffled_pwd)

@router.post("")
async def create_user(data: UserCreate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    temp_password = generate_secure_password()
    hashed_pwd = get_password_hash(temp_password)

    new_user = User(
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        is_approved=True,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send email with temporary password
    try:
        await send_account_created_email(data.email, data.full_name, data.role, temp_password)
    except Exception as e:
        print(f"Failed to send account created email to {data.email}: {e}")
    
    return {"message": "User created successfully", "user_id": str(new_user.id)}

@router.put("/{user_id}")
async def update_user(user_id: str, data: UserUpdate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        # Check if email is being changed and if it already exists
        if data.email != user.email:
            existing = await db.execute(select(User).where(User.email == data.email))
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    return {"message": "User updated successfully"}

@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    # Prevent admin from deleting themselves
    if user_id == str(admin.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    email = user.email
    full_name = user.full_name

    from sqlalchemy import update
    from domain.models.case import Case
    from domain.models.evidence import Evidence
    from domain.models.help_message import HelpMessage
    from domain.models.support import SupportTicket
    from domain.models.takedown import TakedownPolicy

    # Nullify all foreign key constraints manually to prevent IntegrityError
    await db.execute(update(Case).where(Case.submitted_by == user_id).values(submitted_by=None))
    await db.execute(update(Case).where(Case.assigned_to == user_id).values(assigned_to=None))
    await db.execute(update(Evidence).where(Evidence.evidence_owner == user_id).values(evidence_owner=None))
    await db.execute(update(HelpMessage).where(HelpMessage.user_id == user_id).values(user_id=None))
    await db.execute(update(SupportTicket).where(SupportTicket.user_id == user_id).values(user_id=None))
    await db.execute(update(TakedownPolicy).where(TakedownPolicy.approved_by == user_id).values(approved_by=None))

    await db.delete(user)
    await db.commit()

    # Send deletion notification
    try:
        await send_account_deleted_email(email, full_name)
    except Exception as e:
        print(f"Failed to send account deleted email to {email}: {e}")
    
    return {"message": "User deleted successfully"}
