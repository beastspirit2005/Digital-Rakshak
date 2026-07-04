import asyncio
from infrastructure.graph.neo4j_client import IntelligenceGraph

async def main():
    g = IntelligenceGraph()
    res = await g.get_connected_clusters()
    print("CLUSTERS:", res)
    await g.close()

if __name__ == "__main__":
    asyncio.run(main())
