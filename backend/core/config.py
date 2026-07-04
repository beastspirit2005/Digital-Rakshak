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
    GEMINI_API_KEY: str
    GOOGLE_API_KEY: str = ""  # Will be set from GEMINI_API_KEY if not provided
    OLLAMA_HOST: str
    FORCE_LOCAL_INFERENCE: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    ADMIN_EMAIL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

settings = Settings()
