from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.session import get_db
from infrastructure.osint.connector import OSINTConnector
from api.v1.users import get_current_admin
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
