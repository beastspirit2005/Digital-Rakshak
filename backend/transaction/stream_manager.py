import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class TransactionStreamManager:
    """
    Manages active WebSocket and Server-Sent Event (SSE) connections for real-time
    transaction ingestion and human review event streaming.
    """

    def __init__(self):
        self._active_websockets: Set[WebSocket] = set()
        self._active_sse_queues: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    # --------------------------------------------------------------------------
    # WebSocket Lifecycle
    # --------------------------------------------------------------------------
    async def connect_ws(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket client."""
        await websocket.accept()
        async with self._lock:
            self._active_websockets.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self._active_websockets)}")

        # Send welcome/handshake payload
        welcome_payload = {
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Digital Rakshak Real-Time Transaction Intelligence Stream",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(welcome_payload))

    async def disconnect_ws(self, websocket: WebSocket) -> None:
        """Removes a WebSocket client from the active registry."""
        async with self._lock:
            self._active_websockets.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self._active_websockets)}")

    # --------------------------------------------------------------------------
    # Server-Sent Events (SSE) Lifecycle
    # --------------------------------------------------------------------------
    async def connect_sse(self) -> asyncio.Queue:
        """Creates and registers a new event queue for an SSE subscriber."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._active_sse_queues.add(queue)
        logger.info(f"SSE subscriber connected. Active queues: {len(self._active_sse_queues)}")
        return queue

    async def disconnect_sse(self, queue: asyncio.Queue) -> None:
        """Removes an SSE queue when the client connection terminates."""
        async with self._lock:
            self._active_sse_queues.discard(queue)
        logger.info(f"SSE subscriber disconnected. Active queues: {len(self._active_sse_queues)}")

    # --------------------------------------------------------------------------
    # Broadcast Engine
    # --------------------------------------------------------------------------
    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Pushes a real-time event concurrently to all active WebSockets and SSE queues.
        Prunes dead connections automatically without interrupting execution.
        """
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        raw_json = json.dumps(payload, default=str)

        # 1. Broadcast to WebSockets
        dead_websockets: Set[WebSocket] = set()
        async with self._lock:
            ws_targets = list(self._active_websockets)

        for ws in ws_targets:
            try:
                await ws.send_text(raw_json)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket, marking for removal: {e}")
                dead_websockets.add(ws)

        if dead_websockets:
            async with self._lock:
                self._active_websockets.difference_update(dead_websockets)

        # 2. Broadcast to SSE Queues
        sse_formatted = f"event: {event_type}\ndata: {raw_json}\n\n"
        dead_queues: Set[asyncio.Queue] = set()
        async with self._lock:
            sse_targets = list(self._active_sse_queues)

        for q in sse_targets:
            try:
                q.put_nowait(sse_formatted)
            except asyncio.QueueFull:
                logger.warning("SSE queue full, discarding message for slow consumer")
            except Exception as e:
                logger.debug(f"Failed to enqueue to SSE queue: {e}")
                dead_queues.add(q)

        if dead_queues:
            async with self._lock:
                self._active_sse_queues.difference_update(dead_queues)

    @property
    def connection_stats(self) -> Dict[str, int]:
        """Returns the current connection counts."""
        return {
            "websockets": len(self._active_websockets),
            "sse_subscribers": len(self._active_sse_queues)
        }


# Global Singleton Instance
stream_manager = TransactionStreamManager()
