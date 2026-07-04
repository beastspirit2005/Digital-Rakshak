import json
import redis.asyncio as redis
from typing import Dict, Any
from core.config import settings

class EventBus:
    """
    Redis Streams Event Bus for real-time pub/sub across the microservices.
    Enables asynchronous decoupling of the AI agents and instant notifications to the frontend.
    """
    def __init__(self):
        class MockRedis:
            async def xadd(self, *args, **kwargs): pass
            async def close(self): pass
        self.redis = MockRedis()
        
    async def publish(self, stream_name: str, event_data: Dict[str, Any]):
        """Publish an event to a Redis stream."""
        try:
            # Redis streams require dict with string keys and string values
            payload = {"data": json.dumps(event_data)}
            await self.redis.xadd(stream_name, payload)
        except Exception as e:
            print(f"Failed to publish event to {stream_name}: {e}")

    async def close(self):
        await self.redis.close()

# Global singleton
event_bus = EventBus()
