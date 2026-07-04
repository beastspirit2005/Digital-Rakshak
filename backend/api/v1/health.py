import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from infrastructure.db.session import get_db
from infrastructure.db.redis import get_redis
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

    # 2. Check Redis
    try:
        start_time = time.time()
        redis = await get_redis()
        await redis.ping()
        health_status["services"]["redis"] = {
            "status": "up",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["services"]["redis"] = {"status": "down", "error": str(e)}

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

    # Overall Status determination
    if all(s.get("status") == "down" for s in health_status["services"].values()):
        health_status["status"] = "critical"

    return health_status
