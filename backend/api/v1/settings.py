from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

from infrastructure.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from domain.models.settings import PlatformSettings

class SettingsUpdate(BaseModel):
    force_local_inference: bool | None = None
    default_ai_mode: str | None = None

class SettingsResponse(BaseModel):
    force_local_inference: bool
    default_ai_mode: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    ollama_host: str
    gemini_configured: bool

@router.get("/settings")
async def get_platform_settings(db: AsyncSession = Depends(get_db)):
    """Returns current platform settings for admin UI."""
    res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = res.scalar_one_or_none()
    
    return SettingsResponse(
        force_local_inference=db_settings.force_local_inference if db_settings else False,
        default_ai_mode=db_settings.default_ai_mode if db_settings else "auto",
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        ollama_host=settings.OLLAMA_HOST,
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )

@router.put("/settings")
async def update_platform_settings(payload: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Updates runtime platform settings (admin only)."""
    res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = res.scalar_one_or_none()
    
    if not db_settings:
        db_settings = PlatformSettings(id=1, force_local_inference=False, default_ai_mode="auto")
        db.add(db_settings)
    
    if payload.force_local_inference is not None:
        db_settings.force_local_inference = payload.force_local_inference
        settings.FORCE_LOCAL_INFERENCE = payload.force_local_inference
        logger.info(f"FORCE_LOCAL_INFERENCE set to {payload.force_local_inference}")
    
    if payload.default_ai_mode is not None:
        if payload.default_ai_mode not in ("auto", "gemini", "ollama", "both"):
            return {"error": "Invalid ai_mode. Must be auto, gemini, ollama, or both."}
        db_settings.default_ai_mode = payload.default_ai_mode
        logger.info(f"Default AI mode set to {payload.default_ai_mode}")

    await db.commit()
    
    return {
        "status": "ok", 
        "settings": {
            "force_local_inference": db_settings.force_local_inference,
            "default_ai_mode": db_settings.default_ai_mode
        }
    }
