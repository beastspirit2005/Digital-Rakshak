"""
Redis Streams Background Consumer Worker
=========================================
Reads threat events from ``dr:events:stream`` using Redis consumer groups
(``XREADGROUP``) and dispatches them into the RAIC multi-agent pipeline.

Usage
-----
Run as a standalone process alongside the FastAPI server::

    python -m backend.runtime.stream_consumer

Or enable it programmatically via the ``STREAM_CONSUMER_ENABLED=true``
environment variable — it will start as an asyncio background task at
application startup.

Architecture
------------
* Consumer group: ``raic_workers``
* Consumer ID:    ``worker-<hostname>-<pid>``
* Claim interval: 60 s (recovers stalled messages from other workers)
* DLQ threshold:  5 retries → message moved to ``dr:events:failed``
* Graceful shutdown on ``SIGINT`` / ``SIGTERM``

Event schema (JSON in the Redis ``data`` field)
------------------------------------------------
::

    {
        "event_id":   "uuid",
        "event_type": "case_submitted | b2b_event | scan_request",
        "source":     "b2c | b2b_api | internal",
        "tenant_id":  "org-uuid | null",
        "payload":    { ... }   # arbitrary threat data
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
STREAM_EVENTS         = "dr:events:stream"
STREAM_CONSUMER_GROUP = "raic_workers"
STREAM_DLQ            = "dr:events:failed"
CONSUMER_ID           = f"worker-{socket.gethostname()}-{os.getpid()}"
BLOCK_MS              = 5_000    # block up to 5 s per XREADGROUP call
BATCH_SIZE            = 10      # messages per read
MAX_RETRIES           = 5       # move to DLQ after this many delivery attempts
CLAIM_INTERVAL_S      = 60      # recover stalled messages every 60 s


class StreamConsumer:
    """
    Durable Redis Streams consumer using consumer groups.

    Each message is acknowledged (``XACK``) only after successful processing.
    Failed messages are retried up to ``MAX_RETRIES`` times, then moved to the
    DLQ (``dr:events:failed``) with error metadata.
    """

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._running = False
        self._last_claim_time: float = 0.0

    async def _connect(self) -> None:
        """Establish Redis connection and ensure consumer group exists."""
        from core.config import settings
        import redis.asyncio as redis_async

        self._redis = redis_async.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("StreamConsumer connected to Redis. Consumer ID: %s", CONSUMER_ID)

        # Ensure consumer group exists
        try:
            await self._redis.xgroup_create(
                STREAM_EVENTS, STREAM_CONSUMER_GROUP, id="0", mkstream=True
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _process_event(self, message_id: str, data: Dict[str, Any]) -> None:
        """
        Dispatch a single threat event through the RAIC pipeline.

        Currently routes by ``event_type``:
        * ``case_submitted`` → re-analysis / enrichment of existing case
        * ``b2b_event`` → B2B ingestion scoring
        * ``scan_request`` → on-demand scan (guest/consumer)
        * Everything else → logged and acknowledged silently
        """
        event_type = data.get("event_type", "unknown")
        source     = data.get("source", "unknown")
        tenant_id  = data.get("tenant_id")
        payload    = data.get("payload", {})

        logger.info(
            "Processing event [%s] type=%s source=%s tenant=%s",
            message_id, event_type, source, tenant_id,
        )

        try:
            if event_type == "b2b_event":
                await self._handle_b2b_event(tenant_id, payload)
            elif event_type in ("case_submitted", "scan_request"):
                # Lightweight enrichment — heavy lifting happens in the HTTP
                # request path; here we do async graph enrichment / campaign
                # correlation that doesn't block the HTTP response.
                await self._handle_enrichment(payload)
            else:
                logger.debug("Unknown event_type '%s' — skipping.", event_type)

        except Exception as exc:
            logger.error("Error processing event %s: %s", message_id, exc, exc_info=True)
            raise  # let caller handle retry / DLQ logic

    async def _handle_b2b_event(self, tenant_id: Optional[str], payload: Dict[str, Any]) -> None:
        """Score a B2B security event through the threat intelligence pipeline."""
        # Placeholder — full integration wired in b2b.py router via background task
        logger.debug("B2B event scored for tenant %s: %s", tenant_id, payload)

    async def _handle_enrichment(self, payload: Dict[str, Any]) -> None:
        """Async post-processing: graph enrichment and campaign correlation."""
        case_number = payload.get("case_number")
        logger.debug("Async enrichment queued for case %s", case_number)

    async def _move_to_dlq(self, message_id: str, raw_data: str, error: str) -> None:
        """Push an unprocessable message to the Dead-Letter Queue."""
        dlq_payload = {
            "original_stream": STREAM_EVENTS,
            "original_message_id": message_id,
            "error": error,
            "data": raw_data,
        }
        try:
            await self._redis.xadd(
                STREAM_DLQ, {"data": json.dumps(dlq_payload)}, maxlen=10_000, approximate=True
            )
            logger.warning("Moved message %s to DLQ: %s", message_id, error)
        except Exception as exc:
            logger.error("Failed to write message %s to DLQ: %s", message_id, exc)

    async def _claim_stalled_messages(self) -> None:
        """
        Periodically reclaim messages that were delivered to other workers
        but not acknowledged within ``CLAIM_INTERVAL_S`` seconds.
        """
        import time
        now = time.monotonic()
        if now - self._last_claim_time < CLAIM_INTERVAL_S:
            return
        self._last_claim_time = now

        try:
            # XAUTOCLAIM: reclaim messages idle > 60 s
            result = await self._redis.xautoclaim(
                STREAM_EVENTS,
                STREAM_CONSUMER_GROUP,
                CONSUMER_ID,
                min_idle_time=CLAIM_INTERVAL_S * 1000,  # milliseconds
                start_id="0-0",
                count=BATCH_SIZE,
            )
            reclaimed = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else []
            if reclaimed:
                logger.info("Reclaimed %d stalled messages.", len(reclaimed))
        except Exception as exc:
            logger.warning("XAUTOCLAIM failed (may not be supported): %s", exc)

    async def run(self) -> None:
        """Main consumer loop — blocks until ``stop()`` is called."""
        await self._connect()
        self._running = True
        logger.info("StreamConsumer started. Listening on stream '%s'.", STREAM_EVENTS)

        while self._running:
            try:
                await self._claim_stalled_messages()

                # Read a batch of new messages
                results = await self._redis.xreadgroup(
                    STREAM_CONSUMER_GROUP,
                    CONSUMER_ID,
                    {STREAM_EVENTS: ">"},   # ">" = new, undelivered messages
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )

                if not results:
                    continue  # timeout, loop again

                for _stream, messages in results:
                    for message_id, fields in messages:
                        raw_data = fields.get("data", "{}")
                        try:
                            event_data = json.loads(raw_data)
                            await self._process_event(message_id, event_data)
                            # Acknowledge successful processing
                            await self._redis.xack(
                                STREAM_EVENTS, STREAM_CONSUMER_GROUP, message_id
                            )
                        except Exception as exc:
                            # Check delivery count via XPENDING
                            pending = await self._redis.xpending_range(
                                STREAM_EVENTS, STREAM_CONSUMER_GROUP,
                                min=message_id, max=message_id, count=1
                            )
                            delivery_count = pending[0]["times_delivered"] if pending else 1

                            if delivery_count >= MAX_RETRIES:
                                await self._redis.xack(
                                    STREAM_EVENTS, STREAM_CONSUMER_GROUP, message_id
                                )
                                await self._move_to_dlq(message_id, raw_data, str(exc))
                            else:
                                logger.warning(
                                    "Event %s failed (attempt %d/%d), will retry: %s",
                                    message_id, delivery_count, MAX_RETRIES, exc,
                                )

            except asyncio.CancelledError:
                logger.info("StreamConsumer task cancelled — shutting down.")
                break
            except Exception as exc:
                logger.error("StreamConsumer loop error: %s", exc, exc_info=True)
                await asyncio.sleep(2)  # back off before retrying

        await self._shutdown()

    async def stop(self) -> None:
        """Signal the consumer loop to stop gracefully."""
        self._running = False

    async def _shutdown(self) -> None:
        if self._redis:
            await self._redis.aclose()
        logger.info("StreamConsumer shut down cleanly.")


# ── Standalone entrypoint ────────────────────────────────────────────────────

async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    consumer = StreamConsumer()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(consumer.stop()))

    await consumer.run()


if __name__ == "__main__":
    asyncio.run(_main())
