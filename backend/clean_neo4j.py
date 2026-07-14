import asyncio
import sys
sys.path.append('.')
from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select
from infrastructure.graph.neo4j_client import IntelligenceGraph

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case.case_number))
        valid_cases = res.scalars().all()
        
    print(f"Found {len(valid_cases)} valid cases in Postgres.")
    
    graph = IntelligenceGraph()
    async with graph.driver.session() as session:
        # Get all cases in Neo4j
        result = await session.run("MATCH (c:Case) RETURN c.id as case_id")
        records = await result.data()
        neo4j_cases = [r['case_id'] for r in records]
        print(f"Found {len(neo4j_cases)} cases in Neo4j.")
        
        # Find orphans
        orphans = [c for c in neo4j_cases if c not in valid_cases]
        print(f"Found {len(orphans)} orphaned cases in Neo4j: {orphans}")
        
        if orphans:
            # Delete orphaned Case nodes and their relationships
            # We don't delete the PhoneNumber/UPI entities themselves, just the relationships and the Case node
            await session.run("MATCH (c:Case) WHERE c.id IN $orphans DETACH DELETE c", orphans=orphans)
            print("Deleted orphaned cases from Neo4j.")
            
    await graph.close()

asyncio.run(main())
