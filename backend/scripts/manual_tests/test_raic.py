import asyncio
from raic.factory import RAICFactory

async def test_raic():
    try:
        print("Building RAIC DI Container...")
        registry, planner, engine = RAICFactory.build(ai_mode="groq")
        print("RAIC DI Container Built Successfully!")
        
        print("\nRegistered Agents:")
        for agent_name in registry.list_agents():
            print(f"- {agent_name}")
            
        print("\nTest passed! All dependencies are properly wired.")
    except Exception as e:
        import traceback
        print(f"\nERROR: Failed to wire RAIC components: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_raic())
