import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from infrastructure.events.broadcaster import get_broadcaster
from domain.models.user import User
from api.deps import get_current_user_optional, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["Live Event Streaming (SSE)"])


@router.get("/events")
async def stream_live_events(
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Server-Sent Events (SSE) Endpoint (`/api/v1/stream/events`).
    Establishes a persistent real-time stream yielding live AI execution updates, case submissions,
    and takedown alerts to connected browser dashboards (`RAICExecutionMonitor.tsx`).
    Includes 15-second heartbeat keep-alives and proxy unbuffering headers (`X-Accel-Buffering: no`).
    """
    broadcaster = get_broadcaster()

    return StreamingResponse(
        broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/emit", status_code=status.HTTP_200_OK)
async def emit_manual_event(
    event_type: str = Query("agent_execution", description="Event type name"),
    case_id: str = Query("", description="Target case ID/number"),
    agent: str = Query("ThreatAnalysisAgent", description="Agent name"),
    status_msg: str = Query("Running...", description="Status message"),
    execution_ms: int = Query(142, description="Execution time in milliseconds"),
    confidence: float = Query(0.95, description="Confidence score 0.0 to 1.0"),
    admin: Optional[User] = Depends(get_current_user_optional)
):
    """
    Admin utility to manually broadcast a real-time event across all connected SSE clients.
    Useful for testing UI animations, command center responsiveness, and execution monitors.
    """
    broadcaster = get_broadcaster()
    await broadcaster.publish(
        event_type=event_type,
        data={
            "case_id": case_id,
            "agent": agent,
            "status": status_msg,
            "execution_ms": execution_ms,
            "confidence": confidence
        },
        case_id=case_id,
        agent=agent,
        status=status_msg,
        execution_ms=execution_ms,
        confidence=confidence
    )
    return {
        "status": "success",
        "message": f"Broadcasted '{event_type}' for agent '{agent}' ({status_msg}) across active SSE connections."
    }
