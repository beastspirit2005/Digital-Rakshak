from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from shared.contracts.repository import IEvidenceRepository
from shared.contexts.investigation import EvidenceContext
from intelligence.models import DBEvidence
import logging

logger = logging.getLogger(__name__)

class EvidenceRepository(IEvidenceRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_evidence(self, case_id: str, evidence: EvidenceContext) -> None:
        db_ev = await self._session.get(DBEvidence, evidence.evidence_id)
        if not db_ev:
            db_ev = DBEvidence(
                evidence_id=evidence.evidence_id,
                case_id=case_id,
                content_type=evidence.content_type,
                raw_data=evidence.raw_data,
                metadata_json=evidence.metadata
            )
            self._session.add(db_ev)
        else:
            db_ev.raw_data = evidence.raw_data
            db_ev.metadata_json = evidence.metadata
            db_ev.content_type = evidence.content_type
            
        await self._session.commit()
        logger.info(f"Saved Evidence {evidence.evidence_id} to DB.")

    async def get_evidence(self, case_id: str) -> List[EvidenceContext]:
        stmt = select(DBEvidence).where(DBEvidence.case_id == case_id)
        result = await self._session.execute(stmt)
        db_evs = result.scalars().all()
        
        return [
            EvidenceContext(
                evidence_id=ev.evidence_id,
                content_type=ev.content_type,
                raw_data=ev.raw_data,
                metadata=ev.metadata_json
            ) for ev in db_evs
        ]
