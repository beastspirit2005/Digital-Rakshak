import asyncio
import json
from infrastructure.ai.gemini_client import GeminiClient

async def main():
    try:
        client = GeminiClient()
        res = await client.analyze("Tell me a joke", {"context": "none"})
        print("RESULT:")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print("CRASH:")
        print(e)

if __name__ == "__main__":
    import os, sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
    asyncio.run(main())
