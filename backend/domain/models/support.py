import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.db.session import Base
import enum

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    LIVE_CHAT = "live_chat"
    CLOSED = "closed"

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default=TicketStatus.OPEN.value, nullable=False)
    chat_session_ref = Column(String, nullable=True)
    history = Column(JSON, default=list, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
