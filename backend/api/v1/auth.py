import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_otp_email, send_approval_pending_email, send_welcome_email, send_password_reset_otp_email
from domain.models.user import User
from core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "citizen"
    password: str
    
    from pydantic import field_validator
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

class LoginRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    
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

@router.post("/register")
async def register_user(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    is_approved = data.role == "citizen"
    hashed_pwd = get_password_hash(data.password) if data.password else None
    
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        is_approved=is_approved,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    if not is_approved:
        await send_approval_pending_email(data.email, data.role)
        from infrastructure.smtp.email_service import send_email
        from core.config import settings
        admin_subject = f"New {data.role.capitalize()} Registration Pending Approval"
        admin_body = f"A new user ({data.full_name}, {data.email}) has registered for the role of {data.role} and requires your approval."
        await send_email(settings.ADMIN_EMAIL, admin_subject, admin_body)
    else:
        await send_welcome_email(data.email, data.full_name, data.role)

    return {"message": "User registered successfully", "is_approved": is_approved}

@router.post("/request-otp")
async def request_otp(data: LoginRequest, db: AsyncSession = Depends(get_db)):
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
    user.otp = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    
    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        user.otp = None
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {"message": "OTP sent to email successfully."}

@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

    if user.otp != data.otp:
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
        
        user.otp = None
        user.otp_expires_at = None
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
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role
        }
    }

@router.post("/login-password")
async def login_password(data: LoginPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
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
        
    if not verify_password(data.password, user.hashed_password):
        user.otp_failed_attempts += 1
        if user.otp_failed_attempts >= 5:
            user.otp_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            user.otp_failed_attempts = 0
            await db.commit()
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    user.otp_failed_attempts = 0
    user.otp_lockout_count = 0
    user.otp_locked_until = None
    await db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role
        }
    }

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
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
    user.otp = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    
    email_sent = await send_password_reset_otp_email(data.email, otp)
    if not email_sent:
        user.otp = None
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {"message": "Password reset OTP sent to email successfully."}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
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

    if user.otp != data.otp:
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
        
        user.otp = None
        user.otp_expires_at = None
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
