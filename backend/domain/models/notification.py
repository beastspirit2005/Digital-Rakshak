"""
Notification Model
==================
On-platform persistent notification record supporting multi-role alerts:
- Citizens: Case updates, investigator chat replies, safety alerts
- Investigation Officers: Direct case chat pings, new assignments, victim proximity alerts
- Bank Nodal Officers: Urgent takedowns, lien requests, live fraud feed escalations
- Administrators: KYC review queue, misconduct dispute allegations, platform health
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from infrastructure.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default="system_notice")  # chat_message, case_status, kyc_approval, takedown_alert, misconduct_report, system_notice
    priority = Column(String(20), nullable=False, default="normal")     # urgent, high, normal, low
    link = Column(String(500), nullable=True)                          # Clickable URL destination
    metadata_json = Column(JSONB, nullable=True)                        # Context data: case_id, case_number, sender_name, etc.
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    user = relationship("User", backref="notifications")

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "priority": self.priority,
            "link": self.link,
            "metadata": self.metadata_json or {},
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
