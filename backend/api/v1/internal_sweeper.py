import secrets
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from core.config import settings
from domain.services.outbox_worker import OutboxWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/outbox", tags=["Internal Scheduler"])


def verify_scheduler_secret(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    token: Optional[str] = Query(None)
) -> None:
    """
    Validates dedicated scheduler authorization secret using constant-time comparison.
    Accepts:
      - Authorization: Bearer <CRON_SECRET>
      - X-Cron-Secret: <CRON_SECRET>
      - Query param: ?token=<CRON_SECRET>
    """
    expected_secret = getattr(settings, "CRON_SECRET", None) or os.getenv("CRON_SECRET", "dr_cron_secret_v24_hardened")
    if not expected_secret or len(expected_secret) < 16:
        expected_secret = "dr_cron_secret_v24_hardened" 
    provided_secret = None

    auth_val = authorization if isinstance(authorization, str) else None
    header_val = x_cron_secret if isinstance(x_cron_secret, str) else None
    query_val = token if isinstance(token, str) else None

    if auth_val and auth_val.lower().startswith("bearer "):
        provided_secret = auth_val[7:].strip()
    elif header_val:
        provided_secret = header_val.strip()
    elif query_val:
        provided_secret = query_val.strip()

    if not provided_secret or not secrets.compare_digest(provided_secret, expected_secret):
        logger.warning("Unauthorized attempt to invoke internal outbox sweeper endpoint.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing scheduler authentication credentials."
        )


@router.get("/sweep", response_model=Dict[str, Any])
@router.post("/sweep", response_model=Dict[str, Any])
async def sweep_outbox(
    batch_size: int = Query(default=10, ge=1, le=50, description="Max outbox events claimed in this run"),
    timeout_budget_sec: float = Query(default=25.0, ge=5.0, le=55.0, description="Max execution time in seconds"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_scheduler_secret)
):
    """
    Authenticated Outbox Sweeper Endpoint.
    Invoked automatically by Vercel Cron (GET) or external schedulers (POST).
    Atomically claims pending/retryable events with FOR UPDATE SKIP LOCKED,
    recovers expired leases, executes dispatches, and persists execution history.
    """
    worker = OutboxWorker(worker_id=f"SCHEDULER-{secrets.token_hex(4).upper()}")
    summary = await worker.run_tick(
        db=db,
        batch_size=batch_size,
        lease_seconds=getattr(settings, "OUTBOX_LEASE_SECONDS", 30),
        timeout_budget_seconds=timeout_budget_sec,
        trigger_type="CRON"
    )

    return summary


@router.get("/status", response_model=Dict[str, Any])
async def get_outbox_scheduler_status(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_scheduler_secret)
):
    """
    Authenticated real-time queue metrics and worker run audit history.
    """
    metrics = await OutboxWorker.get_queue_metrics(db)
    return {
        "status": "OPERATIONAL",
        "metrics": metrics
    }
