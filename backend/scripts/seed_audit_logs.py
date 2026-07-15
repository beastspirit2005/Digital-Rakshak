import asyncio
import uuid
import sys
import os

# Add backend directory to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from infrastructure.db.session import AsyncSessionLocal
from domain.models.audit_log import AIAuditLog

async def seed_logs():
    print("Seeding AI Audit Logs...")
    async with AsyncSessionLocal() as session:
        logs = [
            AIAuditLog(
                id=uuid.uuid4(),
                officer="SYSTEM_AUTO",
                action="Model Drift Calibration",
                impact="Adjusted Qwen Vision core temperature by -0.02 for stricter OCR",
                verification_hash="0x99e8a71b...",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
            ),
            AIAuditLog(
                id=uuid.uuid4(),
                officer="admin@digitalrakshak.in",
                action="Engine Priority Override",
                impact="Forced Groq Llama 3 as primary text reasoning tier",
                verification_hash="0x11b2c39f...",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1)
            ),
            AIAuditLog(
                id=uuid.uuid4(),
                officer="nodal.delhi@cyberpolice.gov.in",
                action="RLHF Weight Tuning (CASE-2026-8419)",
                impact="Flagged false positive on urgency keyword. Model updated.",
                verification_hash="0x44f1a28d...",
                created_at=datetime.now(timezone.utc) - timedelta(hours=3)
            )
        ]
        
        session.add_all(logs)
        await session.commit()
    print("Seeded 3 audit logs successfully.")

if __name__ == "__main__":
    asyncio.run(seed_logs())
