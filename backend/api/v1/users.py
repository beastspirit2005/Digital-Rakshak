from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from infrastructure.db.session import get_db
from infrastructure.smtp.email_service import send_welcome_email
from domain.models.user import User
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_access_token

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
