import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.db.session import Base
import enum

class HelpMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    ADMIN = "admin"
    SYSTEM = "system"

class HelpMessage(Base):
    __tablename__ = "help_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True) # Optional, can be unauthenticated or anonymous
    role = Column(String, default=HelpMessageRole.USER.value, nullable=False)
    content = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
