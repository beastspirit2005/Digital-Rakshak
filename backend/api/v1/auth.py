import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from infrastructure.db.session import get_db
from infrastructure.db.redis import store_otp, get_otp, delete_otp
from infrastructure.smtp.email_service import send_otp_email, send_approval_pending_email, send_welcome_email
from domain.models.user import User
from core.security import create_access_token, get_password_hash, verify_password
from core.config import settings
import redis.asyncio as redis
from fastapi import Request

router = APIRouter()
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "citizen"
    password: str = None
    
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

@router.post("/register")
async def register_user(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Security: Rate limit registrations per IP to prevent DoS/Botnets
    ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:register:{ip}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, 3600) # 1 hour window
    if current > 3:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many registrations from this IP address.")

    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Auto-approve citizens, require approval for others
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
        # Send pending approval email
        await send_approval_pending_email(data.email, data.role)
        # TODO: Send notification to Admin
    else:
        # Automatically approved citizens get the welcome email immediately
        await send_welcome_email(data.email, data.full_name, data.role)

    return {"message": "User registered successfully", "is_approved": is_approved}

@router.post("/request-otp")
async def request_otp(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        # Don't reveal if user exists or not for security, just return generic message
        return {"message": "If the email is registered and approved, an OTP will be sent."}
    
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    # Generate a secure 6-digit OTP
    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Store in Redis (valid for 5 mins)
    await store_otp(data.email, otp)
    
    # Send email via Brevo
    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {"message": "OTP sent to email successfully."}

@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:verify_otp:{data.email}:{ip}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, 900) # 15 minutes window
    if current > 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed attempts. Try again in 15 minutes.")

    stored_otp = await get_otp(data.email)
    
    if not stored_otp or stored_otp != data.otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    
    # OTP verified, fetch user to generate JWT
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete OTP after successful use and reset rate limit
    await delete_otp(data.email)
    await redis_client.delete(f"rate_limit:verify_otp:{data.email}:{ip}")

    # Generate real JWT
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
    try:
        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:login:{data.email}:{ip}"
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, 900) # 15 minutes window
        if current > 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed attempts. Try again in 15 minutes.")
    except Exception as e:
        return {"debug_error": str(e), "debug_type": str(type(e))}

    try:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        if not user.hashed_password:
            raise HTTPException(status_code=400, detail="This account does not have a password set. Please log in with OTP.")
            
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        if not user.is_approved:
            raise HTTPException(status_code=403, detail="Account pending admin approval.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled.")

        # Reset rate limit on successful login
        await redis_client.delete(f"rate_limit:login:{data.email}:{ip}")

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
    except HTTPException:
        raise
    except Exception as e:
        return {"debug_error": str(e), "debug_type": str(type(e))}
