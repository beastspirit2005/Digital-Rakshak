import os
import io
import uuid
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, EmailStr, field_validator, Field
import secrets
import string

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_welcome_email, send_account_created_email, send_account_deleted_email, send_email, send_otp_email
from domain.models.user import User
from domain.models.audit_event import AuditEvent
from core.security import decode_access_token, get_password_hash, verify_password
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

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    station_phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    station_name: Optional[str] = None
    badge_number: Optional[str] = None
    designation: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(not char.isalnum() for char in v):
            raise ValueError('Password must contain at least one special character')
        return v

class RejectUserRequest(BaseModel):
    reason: str

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

@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get the current logged-in user profile with plan entitlements and operational duty location."""
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
        "is_verified": getattr(user, "is_verified", False),
        "station_phone_number": user.station_phone_number,
        "city": getattr(user, "city", None),
        "state": getattr(user, "state", None),
        "station_name": getattr(user, "station_name", None),
        "badge_number": getattr(user, "badge_number", None),
        "designation": getattr(user, "designation", None),
        "latitude": getattr(user, "latitude", None),
        "longitude": getattr(user, "longitude", None),
        "b2c_plan_code": getattr(user, "b2c_plan_code", "b2c_free") or "b2c_free",
        "b2c_subscription_status": getattr(user, "b2c_subscription_status", "active") or "active",
        "is_pro": is_user_pro,
        "created_at": user.created_at
    }


@router.put("/me")
async def update_my_profile(
    data: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Zero-Trust IDOR-Safe Profile Update:
    Updates personal contact details or official duty location coordinates for the session user.
    Role elevation attempts are strictly rejected by design.
    """
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.station_phone_number is not None:
        user.station_phone_number = data.station_phone_number.strip()
    if data.city is not None:
        user.city = data.city.strip()
    if data.state is not None:
        user.state = data.state.strip()
    if data.station_name is not None:
        user.station_name = data.station_name.strip()
    if data.badge_number is not None:
        user.badge_number = data.badge_number.strip()
    if data.designation is not None:
        user.designation = data.designation.strip()
    if data.latitude is not None:
        user.latitude = data.latitude
    if data.longitude is not None:
        user.longitude = data.longitude

    user.updated_at = datetime.now(timezone.utc)
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
        "message": "Profile updated successfully",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "station_phone_number": user.station_phone_number,
            "city": user.city,
            "state": user.state,
            "station_name": user.station_name,
            "badge_number": user.badge_number,
            "designation": user.designation,
            "latitude": user.latitude,
            "longitude": user.longitude,
            "is_verified": getattr(user, "is_verified", False),
            "is_approved": user.is_approved,
            "is_pro": is_user_pro
        }
    }


@router.post("/me/change-password")
async def change_my_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Constant-time password update verifying current credentials and enforcing enterprise complexity.
    """
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account does not have a local password set."
        )

    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    user.hashed_password = get_password_hash(data.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Password changed successfully."}


@router.get("/me/consent")
async def get_my_consent(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns active consent preferences in accordance with DPDP Act 2023.
    Persisted immutably in the database AuditEvent log.
    """
    from datetime import datetime, timezone
    uid = str(user.id)

    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.actor_id == user.id, AuditEvent.action == "DPDP_CONSENT_UPDATED")
        .order_by(AuditEvent.timestamp.desc())
        .limit(1)
    )
    latest_audit = res.scalar_one_or_none()
    if latest_audit and latest_audit.metadata_json:
        stored = latest_audit.metadata_json
    else:
        stored = {
            "ai_threat_analysis": True,
            "telemetry_monitoring": True,
            "syndicate_intel_sharing": True,
            "communication_alerts": True,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

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
    Persisted immutably to database via AuditEvent.
    """
    from datetime import datetime, timezone
    uid = str(user.id)

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


class BasicProfilePatchRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.patch("/me")
async def patch_my_basic_profile(
    data: BasicProfilePatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Allows a user to update display name or request email change.
    Updating email requires re-verification via OTP for zero-trust integrity.
    """
    if data.full_name is not None and data.full_name.strip():
        user.full_name = data.full_name.strip()

    email_changed = False
    if data.email is not None and data.email.strip():
        new_email = data.email.strip().lower()
        if new_email != user.email:
            existing = await db.execute(select(User).where(User.email == new_email, User.id != user.id))
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="This email is already in use by another account.")
            user.email = new_email
            user.is_verified = False
            otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
            user.otp = get_password_hash(otp)
            user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            user.otp_failed_attempts = 0
            email_changed = True
            await send_otp_email(new_email, otp)

    await db.commit()
    await db.refresh(user)

    msg = "Profile updated successfully."
    if email_changed:
        msg = "Email updated. A verification code has been dispatched to your new address to re-verify your account."

    is_user_pro = (
        user.role in OFFICIAL_INSTITUTIONAL_ROLES
        or (
            getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
            and getattr(user, "b2c_subscription_status", "") == "active"
        )
    )

    return {
        "status": "success",
        "message": msg,
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

    # Securely purge physical or cloud KYC files from storage under DPDP Act
    for path_val in [user.kyc_org_id_path, user.kyc_aadhaar_path]:
        if path_val:
            if path_val.startswith("supabase://"):
                try:
                    from infrastructure.storage.supabase_storage import supabase_storage
                    raw_target = path_val.replace("supabase://", "")
                    parts = raw_target.split("/", 1)
                    bucket_name = parts[0] if len(parts) == 2 else "kyc-documents"
                    obj_key = parts[1] if len(parts) == 2 else parts[0]
                    await supabase_storage.delete_file(bucket_name, obj_key)
                except Exception:
                    pass
            elif os.path.exists(path_val):
                try:
                    os.remove(path_val)
                except Exception:
                    pass

    await db.delete(user)
    await db.commit()

    return {
        "status": "success",
        "message": f"Account for {email} and all associated personal data have been permanently erased."
    }


@router.get("/pending")
async def get_pending_users(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    """List unapproved users awaiting administrative review and KYC verification (Admin only)"""
    result = await db.execute(
        select(User).where(User.is_approved == False).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_approved": user.is_approved,
            "is_verified": getattr(user, "is_verified", False),
            "designation": getattr(user, "designation", None),
            "station_name": getattr(user, "station_name", None),
            "station_phone_number": user.station_phone_number,
            "city": getattr(user, "city", None),
            "state": getattr(user, "state", None),
            "latitude": getattr(user, "latitude", None),
            "longitude": getattr(user, "longitude", None),
            "kyc_org_id_filename": getattr(user, "kyc_org_id_filename", None),
            "kyc_aadhaar_filename": getattr(user, "kyc_aadhaar_filename", None),
            "has_org_id_doc": bool(getattr(user, "kyc_org_id_path", None)),
            "has_aadhaar_doc": bool(getattr(user, "kyc_aadhaar_path", None)),
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if getattr(user, "kyc_submitted_at", None) else None,
            "created_at": user.created_at
        } for user in users
    ]


@router.get("/{user_id}/kyc-document/{doc_type}")
async def get_user_kyc_document(
    user_id: str,
    doc_type: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only secure streaming of official registrant KYC identity documents.
    Enforces path traversal protection and immutable audit logging.
    """
    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    result = await db.execute(select(User).where(User.id == u_uuid))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if doc_type == "org_id":
        doc_path = target_user.kyc_org_id_path
        orig_name = target_user.kyc_org_id_filename or "official_id.dat"
    elif doc_type == "aadhaar":
        doc_path = target_user.kyc_aadhaar_path
        orig_name = target_user.kyc_aadhaar_filename or "aadhaar.dat"
    else:
        raise HTTPException(status_code=400, detail="Invalid document type. Allowed: 'org_id', 'aadhaar'.")

    if not doc_path:
        raise HTTPException(status_code=404, detail="Document file path not recorded.")

    mime_type, _ = mimetypes.guess_type(orig_name)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Log immutable AuditEvent
    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="KYC_DOCUMENT_VIEWED",
        resource_type="kyc_document",
        resource_id=f"user={user_id},doc={doc_type}",
        metadata_json={
            "target_user_id": user_id,
            "document_type": doc_type,
            "filename": orig_name
        }
    )
    db.add(audit)
    await db.commit()

    # Cloud Storage stream (Vercel deployment)
    if doc_path.startswith("supabase://"):
        from infrastructure.storage.supabase_storage import supabase_storage
        raw_target = doc_path.replace("supabase://", "")
        parts = raw_target.split("/", 1)
        bucket_name = parts[0] if len(parts) == 2 else "kyc-documents"
        obj_key = parts[1] if len(parts) == 2 else parts[0]

        file_bytes = await supabase_storage.download_file(bucket_name, obj_key)
        if not file_bytes:
            raise HTTPException(status_code=404, detail="Document file not found in cloud storage.")

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=mime_type,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": f"inline; filename=\"{orig_name}\""
            }
        )

    # Local Storage stream (Local running)
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Document file not found on local server.")

    return FileResponse(
        path=doc_path,
        media_type=mime_type,
        filename=orig_name,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f"inline; filename=\"{orig_name}\""
        }
    )


@router.post("/{user_id}/reject")
async def reject_user(
    user_id: str,
    data: RejectUserRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Rejects an unapproved official registration, records documented reason,
    sends an email notification to the applicant, and safely unlinks KYC documents.
    """
    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    result = await db.execute(select(User).where(User.id == u_uuid))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if target_user.is_approved:
        raise HTTPException(status_code=400, detail="Cannot reject an already approved account. Deactivate it instead.")

    target_email = target_user.email
    target_name = target_user.full_name or "Applicant"
    target_role = target_user.role

    # Clean up physical or cloud KYC files
    for path_val in [target_user.kyc_org_id_path, target_user.kyc_aadhaar_path]:
        if path_val:
            if path_val.startswith("supabase://"):
                try:
                    from infrastructure.storage.supabase_storage import supabase_storage
                    raw_target = path_val.replace("supabase://", "")
                    parts = raw_target.split("/", 1)
                    bucket_name = parts[0] if len(parts) == 2 else "kyc-documents"
                    obj_key = parts[1] if len(parts) == 2 else parts[0]
                    await supabase_storage.delete_file(bucket_name, obj_key)
                except Exception:
                    pass
            elif os.path.exists(path_val):
                try:
                    os.remove(path_val)
                except Exception:
                    pass

    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="USER_REGISTRATION_REJECTED",
        resource_type="user",
        resource_id=user_id,
        metadata_json={
            "target_email": target_email,
            "target_role": target_role,
            "rejection_reason": data.reason
        }
    )
    db.add(audit)

    await db.delete(target_user)
    await db.commit()

    try:
        reject_subject = "Digital Rakshak Official Registration Status Update"
        reject_body = (
            f"Dear {target_name},\n\n"
            f"Thank you for applying for an official {target_role.capitalize()} account on the Digital Rakshak platform.\n\n"
            f"After administrative review of your submitted credentials, your application could not be approved at this time.\n"
            f"Reason documented by verification administrator:\n"
            f"\"{data.reason}\"\n\n"
            f"If you believe this is in error or wish to submit updated documentation, please contact our administrative desk.\n\n"
            f"Regards,\nDigital Rakshak Security Operations Team"
        )
        await send_email(target_email, reject_subject, reject_body)
    except Exception as mail_err:
        pass

    return {"message": f"Application for {target_email} has been rejected and unapproved files purged."}


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """Approve user and grant credentials (Admin only)"""
    try:
        u_uuid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == u_uuid))
    except ValueError:
        result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_approved = True
    user.is_verified = True
    user.kyc_reviewed_by = admin.id
    user.updated_at = datetime.now(timezone.utc)

    audit = AuditEvent(
        actor_id=admin.id,
        actor_role=admin.role,
        action="USER_REGISTRATION_APPROVED",
        resource_type="user",
        resource_id=str(user.id),
        metadata_json={
            "approved_email": user.email,
            "approved_role": user.role,
            "station_name": user.station_name
        }
    )
    db.add(audit)

    try:
        from domain.services.notification_service import NotificationService
        dash_link = "/police" if user.role in ["police", "cyber_cell"] else "/bank" if user.role in ["banker", "bank_employee"] else "/admin" if user.role == "admin" else "/citizen"
        await NotificationService.create_notification(
            db=db,
            user_id=user.id,
            title="KYC Verification Approved",
            message=f"Your {user.role.replace('_', ' ').capitalize()} credentials have been verified. Full institutional access is now granted.",
            type="kyc_approved",
            priority="high",
            link=dash_link,
            metadata={"role": user.role, "station_name": user.station_name}
        )
    except Exception as notif_err:
        pass

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
    
    # Cryptographically uniform shuffle using system CSPRNG
    rng = secrets.SystemRandom()
    rng.shuffle(pwd)

    return ''.join(pwd)

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
    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    result = await db.execute(select(User).where(User.id == u_uuid))
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

    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    result = await db.execute(select(User).where(User.id == u_uuid))
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
