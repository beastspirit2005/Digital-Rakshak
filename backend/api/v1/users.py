from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import string

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_welcome_email, send_account_created_email, send_account_deleted_email
from domain.models.user import User
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_access_token, get_password_hash

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    role: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_admin(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    role = payload.get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
    return payload

async def get_current_user_token(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload

@router.get("/")
async def get_users(db: AsyncSession = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """List all users (Admin only)"""
    result = await db.execute(select(User))
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
async def get_me(db: AsyncSession = Depends(get_db), user_payload: dict = Depends(get_current_user_token)):
    """Get the current logged-in user profile"""
    user_id = user_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/pending")
async def get_pending_users(db: AsyncSession = Depends(get_db), admin: dict = Depends(get_current_admin)):
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
async def approve_user(user_id: str, admin_payload: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_approved = True
    await db.commit()
    
    # Send welcome email now that they are approved
    await send_welcome_email(user.email, user.full_name, user.role)
    
    return {"message": f"User {user.email} has been approved and welcome email sent."}

def generate_secure_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for i in range(length))

@router.post("/")
async def create_user(data: UserCreate, admin_payload: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
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
    await send_account_created_email(data.email, data.full_name, data.role, temp_password)
    
    return {"message": "User created successfully", "user_id": str(new_user.id)}

@router.put("/{user_id}")
async def update_user(user_id: str, data: UserUpdate, admin_payload: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
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
async def delete_user(user_id: str, admin_payload: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    # Prevent admin from deleting themselves
    if user_id == admin_payload.get("sub"):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    email = user.email
    full_name = user.full_name

    await db.delete(user)
    await db.commit()

    # Send deletion notification
    await send_account_deleted_email(email, full_name)
    
    return {"message": "User deleted successfully"}
