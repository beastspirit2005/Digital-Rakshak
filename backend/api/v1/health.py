import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from infrastructure.db.session import get_db
from core.config import settings

from infrastructure.graph.neo4j_client import IntelligenceGraph

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check testing all infrastructure dependencies.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }

    # 1. Check PostgreSQL
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        health_status["services"]["postgres"] = {
            "status": "up",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["services"]["postgres"] = {"status": "down", "error": str(e)}



    # 3. Check Neo4j
    try:
        start_time = time.time()
        graph = IntelligenceGraph()
        # verify_connectivity works on the driver directly
        await graph.driver.verify_connectivity()
        await graph.close()
        health_status["services"]["neo4j"] = {
            "status": "up",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["services"]["neo4j"] = {"status": "down", "error": str(e)}

    # 4. Check AI Provider
    ai_mode = settings.DEFAULT_AI_MODE
    health_status["ai_mode"] = ai_mode
    health_status["services"]["ai"] = {"status": "up"}
    try:
        start_time = time.time()
        if ai_mode == "groq":
            from infrastructure.ai.groq_client import GroqClient
            client = GroqClient()
            # Fast check using 8B model
            await client.generate_text("ping", model_name="llama3-8b-8192")
            health_status["services"]["ai"]["provider"] = "Groq (Cloud)"
            health_status["services"]["ai"]["model"] = "Llama 3 70B/8B"
        else:
            # Check Ollama
            import httpx
            async with httpx.AsyncClient() as httpx_client:
                response = await httpx_client.get(f"{settings.OLLAMA_HOST}")
                response.raise_for_status()
            health_status["services"]["ai"]["provider"] = "Ollama (Offline)"
            health_status["services"]["ai"]["model"] = "Qwen 2.5"
            
        health_status["services"]["ai"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        logger.error(f"AI Provider health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["services"]["ai"]["status"] = "down"
        health_status["services"]["ai"]["error"] = str(e)

    # Overall Status determination
    if all(s.get("status") == "down" for s in health_status["services"].values()):
        health_status["status"] = "critical"

    return health_status
