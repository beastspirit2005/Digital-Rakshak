import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Digital Rakshak"
    API_V1_STR: str = "/v1"
    
    # Database
    DATABASE_URL: str
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    
    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # AI
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None  # For Gemini Flash vision (free tier)
    OLLAMA_HOST: str = "http://localhost:11434"
    FORCE_LOCAL_INFERENCE: bool = False
    DEFAULT_AI_MODE: str = "groq"
    
    
    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    ADMIN_EMAIL: str

    # Supabase / Hybrid Storage
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    LOCAL_FILE_ENCRYPTION_KEY: str = "hkAAmCKwdf2sBS8rbP4VTWI8WWu6bcr3pRT7Jb5nhuo="
    UPLOAD_DIR: str = "/tmp/uploads" if os.environ.get("VERCEL") == "1" else "uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

settings = Settings()
