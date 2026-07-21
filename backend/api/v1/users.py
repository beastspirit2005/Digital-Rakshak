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
from core.security import decode_access_token, get_password_hash
from api.deps import get_current_admin, get_current_user

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

@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get the current logged-in user profile"""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
        "created_at": user.created_at
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
    try:
        await send_welcome_email(user.email, user.full_name, user.role)
    except Exception as e:
        print(f"Failed to send welcome email to {user.email}: {e}")
    
    return {"message": f"User {user.email} has been approved and welcome email sent."}

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
