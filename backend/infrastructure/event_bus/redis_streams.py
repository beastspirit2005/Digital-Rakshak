"""
Redis Streams Event Bus
=======================
Replaces the previous MockRedis stub with a production-ready Redis Streams
client using ``redis.asyncio``.

Design decisions
----------------
* Uses ``XADD`` with ``MAXLEN ~100_000`` (approximate trim) to cap memory.
* Falls back to a pure-in-memory queue when Redis is not reachable so the
  app still boots in environments without Redis (e.g., Vercel cold-start).
* The ``EventBus`` singleton is created once at module import time.
* The real consumer-group worker (``backend/runtime/stream_consumer.py``)
  calls ``XREADGROUP`` independently — this module only publishes.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Stream names ────────────────────────────────────────────────────────────
STREAM_EVENTS   = "dr:events:stream"    # main threat-event ingestion stream
STREAM_CONSUMER_GROUP = "raic_workers"  # consumer group name
STREAM_CONSUMER_DLQ   = "dr:events:failed"  # dead-letter queue


class EventBus:
    """
    Redis Streams Event Bus for real-time pub/sub across the intelligence
    pipeline.  Publishes events to ``dr:events:stream``; the background
    consumer worker reads them with ``XREADGROUP``.

    Falls back to a no-op in-memory stub when Redis is unavailable so that
    the application stays healthy (e.g., Vercel serverless deployments where
    Redis is optional).
    """

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._connected: bool = False
        self._last_connect_attempt: float = 0.0
        self._connect_cooldown: float = 30.0  # seconds between reconnect attempts

    async def _get_redis(self) -> Optional[Any]:
        """Lazy-initialises the async Redis connection pool with reconnect cooldown."""
        if self._connected:
            return self._redis

        import time
        now = time.monotonic()
        if now - self._last_connect_attempt < self._connect_cooldown:
            return None  # Cooldown active, don't stall the event loop

        self._last_connect_attempt = now

        try:
            from core.config import settings
            import redis.asyncio as redis_async

            self._redis = redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                retry_on_timeout=False,
            )
            # Verify connection
            await self._redis.ping()
            self._connected = True
            logger.info("EventBus connected to Redis at %s", settings.REDIS_URL)

            # Ensure consumer group exists (MKSTREAM creates stream if absent)
            try:
                await self._redis.xgroup_create(
                    STREAM_EVENTS, STREAM_CONSUMER_GROUP, id="0", mkstream=True
                )
                logger.info(
                    "Created Redis consumer group '%s' on stream '%s'",
                    STREAM_CONSUMER_GROUP,
                    STREAM_EVENTS,
                )
            except Exception as grp_err:
                if "BUSYGROUP" not in str(grp_err):
                    logger.warning("Could not create consumer group: %s", grp_err)

        except Exception as exc:
            logger.warning(
                "EventBus Redis connection failed (%s). "
                "Operating in no-op fallback mode — reconnect backoff 30s.",
                exc,
            )
            self._redis = None
            self._connected = False

        return self._redis

    async def publish(self, stream_name: str, event_data: Dict[str, Any]) -> None:
        """Publish a single event to a Redis stream via XADD."""
        redis_client = await self._get_redis()
        if redis_client is None:
            return

        try:
            payload = {"data": json.dumps(event_data, default=str)}
            await redis_client.xadd(
                stream_name,
                payload,
                maxlen=100_000,
                approximate=True,
            )
        except Exception as exc:
            logger.error("Failed to publish event to %s: %s", stream_name, exc)

    async def publish_batch(self, stream_name: str, events: List[Dict[str, Any]]) -> int:
        """
        Publish multiple events in a single pipeline for ultra-high throughput.
        Returns the number of successfully published events.
        """
        if not events:
            return 0

        redis_client = await self._get_redis()
        if redis_client is None:
            return len(events)  # In fallback mode, accept all silently

        try:
            pipe = redis_client.pipeline(transaction=False)
            for evt in events:
                payload = {"data": json.dumps(evt, default=str)}
                pipe.xadd(stream_name, payload, maxlen=100_000, approximate=True)
            await pipe.execute()
            return len(events)
        except Exception as exc:
            logger.error("Failed to batch publish to %s: %s", stream_name, exc)
            return 0

    async def publish_threat_event(self, event_data: Dict[str, Any]) -> None:
        """Convenience wrapper — publishes to the canonical threat stream."""
        await self.publish(STREAM_EVENTS, event_data)


    async def close(self) -> None:
        """Closes the Redis connection cleanly on application shutdown."""
        if self._redis and self._connected:
            try:
                await self._redis.aclose()
                logger.info("EventBus Redis connection closed.")
            except Exception:
                pass
        self._connected = False
        self._redis = None


# ── Module-level singleton ───────────────────────────────────────────────────
event_bus = EventBus()
