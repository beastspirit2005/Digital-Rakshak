from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Runtime settings store (persists in memory for this server session)
# In production, this would be stored in Redis or a DB table
_runtime_settings = {
    "force_local_inference": settings.FORCE_LOCAL_INFERENCE,
    "default_ai_mode": "auto",  # auto | gemini | ollama | both
}

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
async def get_platform_settings():
    """Returns current platform settings for admin UI."""
    return SettingsResponse(
        force_local_inference=_runtime_settings["force_local_inference"],
        default_ai_mode=_runtime_settings["default_ai_mode"],
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        ollama_host=settings.OLLAMA_HOST,
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )

@router.put("/settings")
async def update_platform_settings(payload: SettingsUpdate):
    """Updates runtime platform settings (admin only)."""
    if payload.force_local_inference is not None:
        _runtime_settings["force_local_inference"] = payload.force_local_inference
        # Also update the live config so AIRouter picks it up immediately
        settings.FORCE_LOCAL_INFERENCE = payload.force_local_inference
        logger.info(f"FORCE_LOCAL_INFERENCE set to {payload.force_local_inference}")
    
    if payload.default_ai_mode is not None:
        if payload.default_ai_mode not in ("auto", "gemini", "ollama", "both"):
            return {"error": "Invalid ai_mode. Must be auto, gemini, ollama, or both."}
        _runtime_settings["default_ai_mode"] = payload.default_ai_mode
        logger.info(f"Default AI mode set to {payload.default_ai_mode}")

    return {"status": "ok", "settings": _runtime_settings}

def get_default_ai_mode() -> str:
    """Helper for other modules to read the current default AI mode."""
    return _runtime_settings["default_ai_mode"]
