import asyncio
import json
from infrastructure.db.session import AsyncSessionLocal
from api.v1.analytics import get_command_center_telemetry

async def test_endpoint():
    print("Testing command center telemetry logic...")
    async with AsyncSessionLocal() as db:
        result = await get_command_center_telemetry(db=db)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_endpoint())
