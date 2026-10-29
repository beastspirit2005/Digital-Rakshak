import asyncio
from infrastructure.db.session import AsyncSessionLocal
from domain.models.takedown import TakedownPolicy
from domain.agents.takedown_agent import TakedownAgent

async def test_agent():
    print("Testing TakedownAgent against mock APIs...")
    agent = TakedownAgent()
    
    # Test NPCI
    policy_npci = TakedownPolicy(target="scammer@okaxis", action="freeze_account", reason="Fraudulent UPI")
    res_npci = await agent.execute_policy(policy_npci)
    print(f"NPCI Result: {res_npci}")
    
    # Test Telecom
    policy_tel = TakedownPolicy(target="9876543210", action="block_sim", reason="Scam caller")
    res_tel = await agent.execute_policy(policy_tel)
    print(f"Telecom Result: {res_tel}")
    
    await agent.close()

if __name__ == "__main__":
    asyncio.run(test_agent())
