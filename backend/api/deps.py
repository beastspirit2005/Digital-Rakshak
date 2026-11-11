import logging
from typing import Optional, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
import uuid

from infrastructure.db.session import get_db
from core.security import decode_access_token
from domain.models.user import User
from infrastructure.db.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)

# Global Knowledge Base instance to share embedding model memory
kb_instance = None

def get_kb() -> KnowledgeBase:
    global kb_instance
    if kb_instance is None:
        kb_instance = KnowledgeBase()
    return kb_instance

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login-password", auto_error=False)


async def _resolve_user_from_sub(db: AsyncSession, sub: Any) -> Optional[User]:
    """Resolves a user from JWT subject (UUID primary key or fallback email)."""
    if not sub:
        return None
    sub_str = str(sub).strip()
    try:
        user_uuid = uuid.UUID(sub_str)
        res = await db.execute(select(User).where(User.id == user_uuid))
        user = res.scalars().first()
        if user:
            return user
    except (ValueError, TypeError):
        pass
    res = await db.execute(select(User).where(User.email == sub_str.lower()))
    return res.scalars().first()


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        logger.warning("Token decode failed for request to %s", request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Token payload missing sub for request to %s", request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    user = await _resolve_user_from_sub(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
        
    if not user.is_approved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account pending approval")
        
    return user


async def get_current_user_allow_unapproved(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    user = await _resolve_user_from_sub(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
        
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Resolves user from Bearer header or HTTP-only cookie with zero exceptions raised."""
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await _resolve_user_from_sub(db, user_id)
    if not user or not user.is_active:
        return None
    return user


OFFICIAL_INSTITUTIONAL_ROLES = {"admin", "police", "cyber_cell", "banker", "bank_employee"}


async def get_current_user_ws(token: Optional[str], db: AsyncSession) -> User:
    """Validate token and authenticate user over WebSockets."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = await _resolve_user_from_sub(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def require_official_role(user: User = Depends(get_current_user)) -> User:
    """
    Ensures the caller holds an official / institutional role.
    Used by bank escalation, investigation, and sensitive intelligence endpoints.
    Raises HTTP 403 for citizen / consumer accounts.
    """
    if user.role not in OFFICIAL_INSTITUTIONAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorised institutional accounts.",
        )
    return user


async def require_pro_user(user: User = Depends(get_current_user)) -> User:
    """
    Verifies that the user has an active B2C Pro subscription OR is an official / institutional user.
    Police officers, Cyber Cell investigators, Bank Nodal Officers, and Admins work on behalf
    of the organization/state and have complimentary full-tier access without consumer subscription fees.
    Only citizens on the free tier receive HTTP 402 Payment Required.
    """
    if user.role in OFFICIAL_INSTITUTIONAL_ROLES:
        return user

    plan = getattr(user, "b2c_plan_code", "b2c_free")
    status_val = getattr(user, "b2c_subscription_status", "")
    if plan == "b2c_free" or status_val != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Digital Rakshak Pro subscription required for this feature. Upgrade at /personal.",
        )
    return user
