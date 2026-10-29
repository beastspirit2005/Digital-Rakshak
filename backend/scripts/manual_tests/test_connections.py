import asyncio
import os
from core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_postgres():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            logger.info("Successfully connected to Postgres/NeonDB!")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Postgres connection failed: {e}")
        return False

def test_neo4j():
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        logger.info("Successfully connected to Neo4j!")
        driver.close()
        return True
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        return False

async def main():
    pg_ok = await test_postgres()
    n4j_ok = test_neo4j()
    
    if pg_ok and n4j_ok:
        logger.info("ALL DATABASES CONNECTED SUCCESSFULLY!")
    else:
        logger.error("SOME DATABASES FAILED TO CONNECT.")

if __name__ == "__main__":
    asyncio.run(main())
