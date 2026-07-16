import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Set, Optional
from datetime import datetime, timezone

from core.config import settings

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """
    Module 2 — Live Event Streaming (`EventBroadcaster`)
    Manages real-time Server-Sent Events (SSE) broadcasting across connected dashboards.
    Supports high-performance in-memory queues (`asyncio.Queue`) for air-gapped runtimes
    and bridges to Redis Pub/Sub (`redis.asyncio`) when running in cloud production (`REDIS_URL`).
    """
    _instance: Optional["EventBroadcaster"] = None

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._redis_client = None
        self._redis_pubsub = None
        self._is_redis_connected = False

    @classmethod
    def get_instance(cls) -> "EventBroadcaster":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize_redis_if_configured(self):
        """
        Attempts to connect to Redis for multi-node event distribution if REDIS_URL is configured.
        """
        if getattr(settings, "REDIS_URL", None) and not self._is_redis_connected:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                await self._redis_client.ping()
                self._redis_pubsub = self._redis_client.pubsub()
                await self._redis_pubsub.subscribe("raic:events")
                self._is_redis_connected = True
                logger.info("EventBroadcaster successfully bridged to Redis Pub/Sub (raic:events).")
                asyncio.create_task(self._listen_to_redis())
            except Exception as e:
                logger.warning(f"EventBroadcaster Redis connection failed ({e}). Operating in zero-latency local memory mode.")
                self._is_redis_connected = False

    async def _listen_to_redis(self):
        """Background listener forwarding Redis messages to local `asyncio.Queue` subscribers."""
        if not self._redis_pubsub:
            return
        try:
            async for message in self._redis_pubsub.listen():
                if message["type"] == "message":
                    payload = message["data"]
                    await self._dispatch_to_local_queues(payload)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error listening to Redis Pub/Sub: {e}")

    async def _dispatch_to_local_queues(self, sse_payload: str):
        """Pushes an SSE formatted string to all active local client queues."""
        async with self._lock:
            dead_queues = set()
            for queue in self._subscribers:
                try:
                    # Non-blocking put with capacity drop if queue is full (to prevent slow client hangs)
                    if queue.full():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    queue.put_nowait(sse_payload)
                except Exception:
                    dead_queues.add(queue)

            for q in dead_queues:
                self._subscribers.discard(q)

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        case_id: str = "",
        agent: str = "",
        status: str = "",
        execution_ms: int = 0,
        confidence: float = 0.0
    ):
        """
        Publishes a live execution event to all connected dashboards (`RAICExecutionMonitor.tsx` and Command Center).
        Conforms strictly to standard structured event schema while embedding any custom data payload.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build standardized event structure
        structured_payload = {
            "type": event_type,
            "case_id": case_id or str(data.get("case_id", "")),
            "agent": agent or str(data.get("agent", event_type)),
            "status": status or str(data.get("status", "Completed")),
            "execution_ms": execution_ms or int(data.get("execution_ms", 0)),
            "confidence": float(data.get("confidence", confidence)),
            "timestamp": timestamp,
            "data": data
        }

        # Format as strict Server-Sent Event (SSE)
        sse_string = f"event: {event_type}\ndata: {json.dumps(structured_payload)}\n\n"

        # 1. Dispatch locally right away
        await self._dispatch_to_local_queues(sse_string)

        # 2. Publish to Redis if connected
        if self._is_redis_connected and self._redis_client:
            try:
                await self._redis_client.publish("raic:events", sse_string)
            except Exception as e:
                logger.warning(f"Failed to publish event to Redis: {e}")

    async def emit_agent_event(
        self,
        case_id: str,
        agent_name: str,
        status: str,
        execution_ms: int = 0,
        confidence: float = 0.0,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Helper method specifically tuned for RAIC agents (`ThreatAnalysisAgent`, `BehaviourAnalysisAgent`, `DecisionCore`)
        to emit real-time status changes (`Running...`, `Completed`, `Waiting...`).
        """
        event_data = {
            "case_id": case_id,
            "agent": agent_name,
            "status": status,
            "execution_ms": execution_ms,
            "confidence": confidence,
            "message": message,
            "metadata": metadata or {}
        }
        await self.publish(
            event_type="agent_execution",
            data=event_data,
            case_id=case_id,
            agent=agent_name,
            status=status,
            execution_ms=execution_ms,
            confidence=confidence
        )

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        SSE subscription generator. Yields data frames and periodic heartbeat keep-alives every 15 seconds.
        """
        await self.initialize_redis_if_configured()
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        async with self._lock:
            self._subscribers.add(queue)

        logger.debug(f"New SSE client connected. Active subscribers: {len(self._subscribers)}")

        try:
            # Send immediate initial connection confirmation
            welcome_payload = {
                "type": "connection_established",
                "message": "Connected to Digital Rakshak Live Event Stream",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"event: connected\ndata: {json.dumps(welcome_payload)}\n\n"

            while True:
                try:
                    # Wait for next event with 15-second heartbeat timeout
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send SSE heartbeat comment to prevent proxy / browser timeout disconnects
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                self._subscribers.discard(queue)
            logger.debug(f"SSE client disconnected. Active subscribers: {len(self._subscribers)}")


def get_broadcaster() -> EventBroadcaster:
    """Convenience getter for the global singleton EventBroadcaster."""
    return EventBroadcaster.get_instance()
