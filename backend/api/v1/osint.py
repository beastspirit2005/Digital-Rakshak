from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.session import get_db
from infrastructure.osint.connector import OSINTConnector
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/sync")
async def sync_osint_feeds(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_admin)):
    """
    Admin-only endpoint to sync public threat intelligence (OSINT) feeds 
    into the Intelligent Database (Postgres & Neo4j).
    """
    try:
        connector = OSINTConnector()
        result = await connector.sync_public_feeds(db)
        return result
    except Exception as e:
        logger.error(f"Failed to sync OSINT feeds: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OSINT Sync Failed")

@router.post("/kb/seed")
async def seed_knowledge_base(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_admin)):
    """
    Admin-only endpoint to seed the pgvector knowledge base with mock RBI Guidelines and Public Fraud Patterns.
    """
    from api.deps import get_kb
    kb = get_kb()
    try:
        await kb.seed_knowledge_base(db)
        return {"status": "success", "message": "Knowledge base seeded successfully with vectors."}
    except Exception as e:
        logger.error(f"Failed to seed knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge Base seeding failed: {e}")

@router.get("/scan-case/{case_number}")
async def scan_case_osint(case_number: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Scans a case's extracted entities (Phone, URL, UPI, etc.) against global OSINT threat intelligence.
    Returns matched ThreatIntel flags.
    """
    if current_user.role not in ["admin", "police", "cyber_cell"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    from infrastructure.graph.neo4j_client import IntelligenceGraph
    graph = IntelligenceGraph()
    try:
        # Get entities from Neo4j associated with this case
        entities = await graph.get_entities_for_case(case_number)
        
        if not entities:
            return {"flags": []}
            
        # Match against ThreatIntel
        flags = await graph.get_osint_flags_for_entities(entities)
        return {"flags": flags}
    except Exception as e:
        logger.error(f"Failed to scan case {case_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to run OSINT scan")
    finally:
        await graph.close()
