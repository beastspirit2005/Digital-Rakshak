import asyncio
from infrastructure.graph.neo4j_client import IntelligenceGraph

async def test_neo4j():
    try:
        graph = IntelligenceGraph()
        driver = graph.driver
        async with driver.session() as session:
            result = await session.run("RETURN 1 as num")
            record = await result.single()
            if record and record["num"] == 1:
                print("Successfully connected to Neo4j!")
            else:
                print("Neo4j returned unexpected result.")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")

asyncio.run(test_neo4j())
