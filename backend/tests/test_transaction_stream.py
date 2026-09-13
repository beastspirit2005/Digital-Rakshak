import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from transaction.stream_manager import TransactionStreamManager, stream_manager


@pytest.mark.asyncio
async def test_stream_manager_broadcast():
    """Unit test for stream manager broadcasting to websockets and sse."""
    mgr = TransactionStreamManager()

    # Mock WebSocket
    mock_ws = AsyncMock()
    await mgr.connect_ws(mock_ws)
    assert mock_ws in mgr._active_websockets
    assert mock_ws.send_text.await_count == 1  # Handshake sent

    # Connect SSE
    sse_q = await mgr.connect_sse()
    assert sse_q in mgr._active_sse_queues

    # Broadcast event
    test_data = {"transaction_id": "TXN-STREAM-001", "amount": 1500.0}
    await mgr.broadcast("TRANSACTION_INGESTED", test_data)

    # Verify WS received text
    assert mock_ws.send_text.await_count == 2
    last_ws_call = mock_ws.send_text.call_args[0][0]
    ws_json = json.loads(last_ws_call)
    assert ws_json["type"] == "TRANSACTION_INGESTED"
    assert ws_json["data"]["transaction_id"] == "TXN-STREAM-001"

    # Verify SSE received message
    assert not sse_q.empty()
    sse_msg = await sse_q.get()
    assert "event: TRANSACTION_INGESTED" in sse_msg
    assert "TXN-STREAM-001" in sse_msg

    # Test disconnection
    await mgr.disconnect_ws(mock_ws)
    await mgr.disconnect_sse(sse_q)
    assert mock_ws not in mgr._active_websockets
    assert sse_q not in mgr._active_sse_queues


def test_websocket_endpoint_handshake_and_ping():
    """Integration test for /v1/transactions/ws endpoint using TestClient."""
    client = TestClient(app)
    with client.websocket_connect("/v1/transactions/ws") as ws:
        # Handshake
        init_data = ws.receive_json()
        assert init_data["type"] == "CONNECTION_ESTABLISHED"

        # Send PING
        ws.send_text(json.dumps({"type": "PING"}))
        pong_data = ws.receive_json()
        assert pong_data["type"] == "PONG"
