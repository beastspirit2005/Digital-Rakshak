from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional

from shared.contracts.repository import IInvestigationRepository
from shared.contexts.investigation import InvestigationContext, ExecutionContext, InvestigationMetadata, EvidenceContext, RuntimeContext
from intelligence.models import DBInvestigation, DBExecution, DBEvidence
import logging

logger = logging.getLogger(__name__)

class InvestigationRepository(IInvestigationRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_investigation(self, context: InvestigationContext) -> None:
        db_inv = await self._session.get(DBInvestigation, context.case_id)
        if not db_inv:
            # Create Execution
            db_exec = DBExecution(
                correlation_id=context.execution.correlation_id,
                actor_id=context.execution.actor_id,
                started_at=context.execution.started_at
            )
            self._session.add(db_exec)
            
            # Create Investigation
            db_inv = DBInvestigation(
                case_id=context.case_id,
                status=context.metadata.current_status,
                confidence_score=context.metadata.confidence_score,
                tags=context.metadata.tags,
                execution_id=context.execution.correlation_id
            )
            self._session.add(db_inv)
        else:
            # Update Investigation
            db_inv.status = context.metadata.current_status
            db_inv.confidence_score = context.metadata.confidence_score
            db_inv.tags = context.metadata.tags

        await self._session.commit()
        logger.info(f"Saved Investigation {context.case_id} to DB.")

    async def get_investigation(self, case_id: str) -> Optional[InvestigationContext]:
        stmt = select(DBInvestigation).options(
            selectinload(DBInvestigation.execution),
            selectinload(DBInvestigation.evidence)
        ).where(DBInvestigation.case_id == case_id)
        
        result = await self._session.execute(stmt)
        db_inv = result.scalar_one_or_none()
        
        if not db_inv:
            return None
            
        execution = ExecutionContext(
            correlation_id=db_inv.execution.correlation_id,
            actor_id=db_inv.execution.actor_id,
            started_at=db_inv.execution.started_at
        ) if db_inv.execution else ExecutionContext(correlation_id="legacy", actor_id="system")
        
        metadata = InvestigationMetadata(
            current_status=db_inv.status,
            confidence_score=db_inv.confidence_score,
            tags=db_inv.tags
        )
        
        evidence_list = []
        for ev in db_inv.evidence:
            evidence_list.append(EvidenceContext(
                evidence_id=ev.evidence_id,
                content_type=ev.content_type,
                raw_data=ev.raw_data,
                metadata=ev.metadata_json
            ))
            
        return InvestigationContext(
            case_id=db_inv.case_id,
            execution=execution,
            metadata=metadata,
            evidence=evidence_list,
            runtime=RuntimeContext()
        )
