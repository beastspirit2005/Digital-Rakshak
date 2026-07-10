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
    OLLAMA_HOST: str
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
    LOCAL_FILE_ENCRYPTION_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

settings = Settings()
