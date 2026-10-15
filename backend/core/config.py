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
    OLLAMA_MODEL: str = "llama3:8b"
    FORCE_LOCAL_INFERENCE: bool = False
    DEFAULT_AI_MODE: str = "groq"
    
    # Redis — used for real-time event streaming and guest scan rate-limiting
    # Local: redis://localhost:6379/0
    # Production (Upstash): rediss://<TOKEN>@<HOST>:6380
    REDIS_URL: str = "redis://localhost:6379/0"
    # Set to "true" to start background stream consumer worker process
    STREAM_CONSUMER_ENABLED: bool = False

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
    LOCAL_FILE_ENCRYPTION_KEY: str
    UPLOAD_DIR: str = "/tmp/uploads" if os.environ.get("VERCEL") == "1" else "uploads"

    # Razorpay — Payment gateway (India UPI AutoPay + Cards)
    # Create account at https://dashboard.razorpay.com
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(_base_dir, ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
