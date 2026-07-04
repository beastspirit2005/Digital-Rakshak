from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from infrastructure.db.session import Base

class ScamPattern(Base):
    """
    Supervised Learning Dataset Model.
    Stores verified OSINT scam examples (e.g., from public threat intelligence).
    """
    __tablename__ = "scam_patterns"

    id = Column(Integer, primary_key=True, index=True)
    scam_type = Column(String, index=True) # e.g. "DIGITAL_ARREST", "FEDEX_SCAM"
    source = Column(String) # e.g. "OSINT_CONNECTOR", "PHISHTANK"
    raw_text_example = Column(Text) # The actual script or message used by scammers
    modus_operandi = Column(Text) # AI summary of how it works
    indicators_of_compromise = Column(JSON, default=dict) # {"phone_numbers": [], "urls": []}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
