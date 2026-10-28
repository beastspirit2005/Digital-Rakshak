import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_otp_email, send_approval_pending_email, send_welcome_email, send_password_reset_otp_email, send_email
from domain.models.user import User
from core.security import create_access_token, get_password_hash, verify_password
from core.file_security import validate_and_save_kyc_file
from core.config import settings
from api.deps import OFFICIAL_INSTITUTIONAL_ROLES
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "citizen"
    password: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str):
        if v == "admin":
            raise ValueError("Admin accounts cannot be self-registered. Please contact an existing system administrator.")
        role_map = {
            "citizen": "citizen",
            "police": "police",
            "cyber_cell": "cyber_cell",
            "banker": "bank_employee",
            "bank_employee": "bank_employee"
        }
        if v not in role_map:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: citizen, police, cyber_cell, banker")
        return role_map[v]
    
    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not any(char.isdigit() for char in v):
                raise ValueError('Password must contain at least one digit')
            if not any(not char.isalnum() for char in v):
                raise ValueError('Password must contain at least one special character')
        return v

class LoginPasswordRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class LoginRequest(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    
    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v
    
    from pydantic import field_validator
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not any(char.isdigit() for char in v):
                raise ValueError('Password must contain at least one digit')
            if not any(not char.isalnum() for char in v):
                raise ValueError('Password must contain at least one special character')
        return v

class VerifyRegistrationOTPRequest(BaseModel):
    email: EmailStr
    otp: str

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

class ResendOTPRequest(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def lower_email(cls, v: str):
        return v.lower() if v else v

@router.post("/register")
@limiter.limit("10/minute")
async def register_user(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of Citizen Registration:
    Creates account in pending verification state and dispatches a 6-digit CSPRNG Email OTP.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        if getattr(existing_user, "is_verified", False):
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        # If registered but unverified, refresh password and resend fresh OTP
        user = existing_user
        if data.password:
            user.hashed_password = get_password_hash(data.password)
        if data.full_name:
            user.full_name = data.full_name
    else:
        hashed_pwd = get_password_hash(data.password) if data.password else None
        user = User(
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            is_approved=False,
            is_verified=False,
            hashed_password=hashed_pwd
        )
        db.add(user)
    
    # Generate 6-digit cryptographic OTP
    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.otp = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    user.otp_failed_attempts = 0
    await db.commit()
    await db.refresh(user)

    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        logger.warning("Could not dispatch registration OTP email to %s (using local/sandbox mode)", data.email)

    return {
        "message": "Verification code dispatched to your email. Please verify OTP to activate your account.",
        "email": data.email,
        "requires_otp": True,
        "role": data.role
    }


@router.post("/register-official")
@limiter.limit("5/minute")
async def register_official(
    request: Request,
    email: EmailStr = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    designation: Optional[str] = Form(None),
    station_name: Optional[str] = Form(None),
    station_phone_number: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    org_id_file: UploadFile = File(...),
    aadhaar_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1 of Official Institutional Registration:
    Enforces role-based KYC uploads (Company ID, Police Badge, Bank ID + Aadhaar Card),
    validates magic bytes & 5MB file limit, captures duty location GPS, and dispatches Email OTP.
    """
    # Normalize & validate role
    role_clean = role.lower().strip()
    if role_clean == "admin":
        raise HTTPException(
            status_code=400,
            detail="Admin accounts cannot be self-registered. Only authorized system administrators can provision administrator accounts."
        )

    role_map = {
        "police": "police",
        "cyber_cell": "cyber_cell",
        "banker": "bank_employee",
        "bank_employee": "bank_employee"
    }
    if role_clean not in role_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid official role '{role}'. Allowed official roles: police, cyber_cell, banker"
        )
    mapped_role = role_map[role_clean]

    # Validate password complexity
    if len(password) < 8 or not any(c.isdigit() for c in password) or not any(not c.isalnum() for c in password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long, contain at least one digit and one special character."
        )

    clean_email = email.lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    existing_user = res.scalars().first()
    if existing_user and getattr(existing_user, "is_verified", False):
        raise HTTPException(status_code=400, detail="An account with this official email already exists.")

    user_id = existing_user.id if existing_user else uuid.uuid4()

    # Zero-Trust KYC Magic Bytes and 5MB validation
    org_id_path, org_id_filename, _ = await validate_and_save_kyc_file(
        org_id_file, user_id=user_id, doc_type="official_id"
    )
    aadhaar_path, aadhaar_filename, _ = await validate_and_save_kyc_file(
        aadhaar_file, user_id=user_id, doc_type="aadhaar"
    )

    hashed_pwd = get_password_hash(password)

    if existing_user:
        user = existing_user
        user.full_name = full_name
        user.hashed_password = hashed_pwd
        user.role = mapped_role
        user.designation = designation
        user.station_name = station_name
        user.station_phone_number = station_phone_number
        user.city = city
        user.state = state
        user.latitude = latitude
        user.longitude = longitude
        user.kyc_org_id_path = org_id_path
        user.kyc_org_id_filename = org_id_filename
        user.kyc_aadhaar_path = aadhaar_path
        user.kyc_aadhaar_filename = aadhaar_filename
        user.kyc_submitted_at = datetime.now(timezone.utc)
    else:
        user = User(
            id=user_id,
            email=clean_email,
            full_name=full_name,
            hashed_password=hashed_pwd,
            role=mapped_role,
            is_approved=False,
            is_verified=False,
            designation=designation,
            station_name=station_name,
            station_phone_number=station_phone_number,
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            kyc_org_id_path=org_id_path,
            kyc_org_id_filename=org_id_filename,
            kyc_aadhaar_path=aadhaar_path,
            kyc_aadhaar_filename=aadhaar_filename,
            kyc_submitted_at=datetime.now(timezone.utc)
        )
        db.add(user)

    # Generate 6-digit cryptographic registration OTP
    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.otp = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    user.otp_failed_attempts = 0
    await db.commit()
    await db.refresh(user)

    await send_otp_email(clean_email, otp)

    return {
        "message": "Official credentials and KYC documents uploaded. Verification code dispatched to your email.",
        "email": clean_email,
        "requires_otp": True,
        "role": mapped_role,
        "org_id_filename": org_id_filename,
        "aadhaar_filename": aadhaar_filename
    }


@router.post("/verify-registration-otp")
@limiter.limit("10/minute")
async def verify_registration_otp(request: Request, data: VerifyRegistrationOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of Registration (Citizens & Officials):
    Validates the 6-digit Email OTP:
    - Citizens are activated immediately (is_approved=True) and issued a session token.
    - Officials are verified (is_verified=True) and queued for Administrator KYC document review.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="No pending registration found for this email.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Too many attempts. Account locked for {remaining} seconds.")
        user.otp_locked_until = None

    if not user.otp:
        raise HTTPException(status_code=400, detail="No active verification code. Please request a new OTP.")

    expires_at = user.otp_expires_at.replace(tzinfo=timezone.utc) if user.otp_expires_at and user.otp_expires_at.tzinfo is None else user.otp_expires_at
    if not expires_at or expires_at < datetime.now(timezone.utc):
        user.otp = None
        user.otp_expires_at = None
        await db.commit()
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if not verify_password(data.otp, user.otp):
        user.otp_failed_attempts += 1
        if user.otp_failed_attempts >= 3:
            user.otp_locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
            user.otp = None
            user.otp_expires_at = None
            user.otp_failed_attempts = 0
            await db.commit()
            raise HTTPException(status_code=429, detail="Too many invalid attempts. Temporarily locked for 10 minutes.")
        await db.commit()
        raise HTTPException(status_code=401, detail=f"Invalid OTP code. {3 - user.otp_failed_attempts} attempt(s) remaining.")

    # OTP Verified Successfully
    user.otp = None
    user.otp_expires_at = None
    user.otp_failed_attempts = 0
    user.otp_lockout_count = 0
    user.otp_locked_until = None
    user.is_verified = True

    if user.role == "citizen":
        user.is_approved = True
        await db.commit()
        await db.refresh(user)

        try:
            await send_welcome_email(user.email, user.full_name or "Citizen", user.role)
        except Exception as mail_err:
            logger.warning("Failed to dispatch welcome email: %s", mail_err)

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )

        return {
            "message": "Email verified successfully. Welcome to Digital Rakshak!",
            "access_token": access_token,
            "token_type": "bearer",
            "is_approved": True,
            "role": user.role,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_verified": True,
                "is_approved": True,
                "is_pro": False
            }
        }
    else:
        # Official account requires Administrator KYC Review
        user.is_approved = False
        await db.commit()
        await db.refresh(user)

        # Notify platform administrators on-platform
        try:
            from domain.services.notification_service import NotificationService
            await NotificationService.notify_admins(
                db=db,
                title="📋 New Official KYC Verification Queued",
                message=f"{user.full_name} ({user.role}) submitted credentials for {user.station_name or 'Station'}.",
                type="kyc_approval",
                priority="high",
                link="/admin/approvals",
                metadata={"applicant_id": str(user.id), "role": user.role},
            )
            await db.commit()
        except Exception as e:
            logger.warning("Failed to queue admin KYC on-platform notification: %s", e)

        try:
            await send_approval_pending_email(user.email, user.role)
            admin_subject = f"New {user.role.capitalize()} Registration Pending KYC Approval"
            admin_body = (
                f"Official applicant {user.full_name} ({user.email}) has verified their email.\n"
                f"Role: {user.role}\n"
                f"Station/Branch: {user.station_name or 'N/A'}\n"
                f"Designation: {user.designation or 'N/A'}\n"
                f"KYC Documents: Uploaded and awaiting inspection in the Approvals Console."
            )
            await send_email(settings.ADMIN_EMAIL, admin_subject, admin_body)
        except Exception as mail_err:
            logger.warning("Failed to send official review notification emails: %s", mail_err)

        return {
            "message": "Email verified successfully! Your official credentials and KYC identity documents have been submitted to platform administrators for verification.",
            "is_approved": False,
            "role": user.role,
            "email": user.email
        }


@router.post("/resend-registration-otp")
@limiter.limit("3/minute")
async def resend_registration_otp(request: Request, data: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    """Resends a fresh 6-digit registration OTP to unverified accounts."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="Account is already verified. Please sign in.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None

    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.otp = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    # Do not reset user.otp_failed_attempts to prevent lockout bypass
    await db.commit()

    await send_otp_email(data.email, otp)
    return {"message": "A fresh 6-digit verification code has been dispatched to your email."}

@router.post("/request-otp")
@limiter.limit("5/minute")
async def request_otp(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        return {"message": "If the email is registered and approved, an OTP will be sent."}
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None

    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.otp = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    
    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        user.otp = None
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {"message": "OTP sent to email successfully."}

@router.post("/verify-otp")
@limiter.limit("10/minute")
async def verify_otp(request: Request, data: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not getattr(user, "is_verified", False):
        raise HTTPException(status_code=403, detail="Email verification required. Please complete registration OTP verification.")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None

    if not user.otp:
        raise HTTPException(status_code=401, detail="No active OTP. Please request a new one.")
        
    expires_at = user.otp_expires_at.replace(tzinfo=timezone.utc) if user.otp_expires_at and user.otp_expires_at.tzinfo is None else user.otp_expires_at
    if not expires_at or expires_at < datetime.now(timezone.utc):
        user.otp = None
        user.otp_expires_at = None
        await db.commit()
        raise HTTPException(status_code=401, detail="OTP code expired. Please request a new one.")

    if not verify_password(data.otp, user.otp):
        user.otp_failed_attempts += 1
        if user.otp_failed_attempts >= 3:
            user.otp_lockout_count += 1
            tiers = [5, 10, 15, None]
            idx = min(user.otp_lockout_count - 1, 3)
            lock_duration = tiers[idx]
            if lock_duration is not None:
                user.otp_locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration)
                detail_msg = f"Too many failed attempts. Account locked for {lock_duration} minutes."
            else:
                user.is_active = False
                detail_msg = "Account permanently locked due to repeated failed attempts."
            user.otp = None
            user.otp_expires_at = None
            user.otp_failed_attempts = 0
            await db.commit()
            raise HTTPException(status_code=429, detail=detail_msg)
        
        await db.commit()
        raise HTTPException(status_code=401, detail=f"Invalid OTP code. {3 - user.otp_failed_attempts} attempt(s) remaining.")

    user.otp = None
    user.otp_expires_at = None
    user.otp_failed_attempts = 0
    user.otp_lockout_count = 0
    user.otp_locked_until = None
    await db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    is_user_pro = (
        user.role in OFFICIAL_INSTITUTIONAL_ROLES
        or (
            getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
            and getattr(user, "b2c_subscription_status", "") == "active"
        )
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
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

@router.post("/login-password")
@limiter.limit("10/minute")
async def login_password(request: Request, data: LoginPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None
        
    if not user.hashed_password:
        raise HTTPException(status_code=400, detail="This account does not have a password set. Please log in with OTP.")

    if not getattr(user, "is_verified", False):
        raise HTTPException(status_code=403, detail="Email verification required. Please complete registration OTP verification.")

    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")
        
    if not verify_password(data.password, user.hashed_password):
        user.otp_failed_attempts += 1
        if user.otp_failed_attempts >= 5:
            user.otp_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            user.otp_failed_attempts = 0
            await db.commit()
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.otp_failed_attempts = 0
    user.otp_lockout_count = 0
    user.otp_locked_until = None
    await db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    is_user_pro = (
        user.role in OFFICIAL_INSTITUTIONAL_ROLES
        or (
            getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
            and getattr(user, "b2c_subscription_status", "") == "active"
        )
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
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

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        return {"message": "If the email is registered, a password reset OTP will be sent."}
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None

    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.otp = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    
    email_sent = await send_password_reset_otp_email(data.email, otp)
    if not email_sent:
        user.otp = None
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {"message": "Password reset OTP sent to email successfully."}

@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    if user.otp_locked_until:
        locked_until = user.otp_locked_until.replace(tzinfo=timezone.utc) if user.otp_locked_until.tzinfo is None else user.otp_locked_until
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(status_code=429, detail=f"Account is temporarily locked. Try again in {remaining} seconds.")
        user.otp_locked_until = None

    if not user.otp:
        raise HTTPException(status_code=401, detail="No active OTP. Please request a new one.")
        
    expires_at = user.otp_expires_at.replace(tzinfo=timezone.utc) if user.otp_expires_at and user.otp_expires_at.tzinfo is None else user.otp_expires_at
    if not expires_at or expires_at < datetime.now(timezone.utc):
        user.otp = None
        user.otp_expires_at = None
        await db.commit()
        raise HTTPException(status_code=401, detail="OTP code expired. Please request a new one.")

    if not verify_password(data.otp, user.otp):
        user.otp_failed_attempts += 1
        if user.otp_failed_attempts >= 3:
            user.otp_lockout_count += 1
            tiers = [5, 10, 15, None]
            idx = min(user.otp_lockout_count - 1, 3)
            lock_duration = tiers[idx]
            if lock_duration is not None:
                user.otp_locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration)
                detail_msg = f"Too many failed attempts. Account locked for {lock_duration} minutes."
            else:
                user.is_active = False
                detail_msg = "Account permanently locked due to repeated failed attempts."
            user.otp = None
            user.otp_expires_at = None
            user.otp_failed_attempts = 0
            await db.commit()
            raise HTTPException(status_code=429, detail=detail_msg)
        
        await db.commit()
        raise HTTPException(status_code=401, detail=f"Invalid OTP code. {3 - user.otp_failed_attempts} attempt(s) remaining.")

    # OTP is valid!
    user.otp = None
    user.otp_expires_at = None
    user.otp_failed_attempts = 0
    user.otp_lockout_count = 0
    user.otp_locked_until = None
    
    # Update password
    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Password successfully reset."}
