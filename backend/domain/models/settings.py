from sqlalchemy import Column, String, Boolean, Integer
from infrastructure.db.session import Base

class PlatformSettings(Base):
    __tablename__ = "platform_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    force_local_inference = Column(Boolean, default=False)
    default_ai_mode = Column(String, default="auto")
