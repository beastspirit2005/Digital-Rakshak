import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8000/api/v1/help/ws/citizen/test_client"
    async with websockets.connect(uri) as ws:
        print("Connected!")
        await ws.send(json.dumps({"type": "chat", "content": "Hello", "model": "groq"}))
        res1 = await ws.recv()
        print("Response 1:", res1)
        res2 = await ws.recv()
        print("Response 2:", res2)

asyncio.run(test())
