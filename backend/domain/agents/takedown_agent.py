import httpx
import logging
from domain.models.takedown import TakedownPolicy

logger = logging.getLogger(__name__)

class TakedownAgent:
    """
    Executes a generated TakedownPolicy by dispatching HTTP requests to external partner networks.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/v1/mock-apis"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def execute_policy(self, policy: TakedownPolicy) -> dict:
        """
        Routes the policy action to the correct external endpoint.
        """
        try:
            if policy.action in ["freeze_account", "block_upi"]:
                # Route to NPCI
                res = await self.client.post(
                    f"{self.base_url}/npci/freeze-upi",
                    json={"target_id": policy.target, "reason": policy.reason}
                )
                res.raise_for_status()
                return res.json()
                
            elif policy.action in ["block_imei", "block_sim", "block_phone"]:
                # Route to Telecom
                res = await self.client.post(
                    f"{self.base_url}/telecom/block-sim",
                    json={"phone_number": policy.target, "reason": policy.reason}
                )
                res.raise_for_status()
                return res.json()
                
            elif policy.action in ["block_domain", "block_url"]:
                # Mock registry
                logger.info(f"Mocking domain block for {policy.target}")
                return {"status": "success", "action_taken": "DOMAIN_BLOCKED", "receipt": "DOM-123"}
            else:
                logger.warning(f"Unknown takedown action: {policy.action}")
                return {"error": "Unsupported action"}
                
        except Exception as e:
            logger.error(f"Failed to execute takedown on target {policy.target}: {e}")
            return {"error": str(e)}

    async def close(self):
        await self.client.aclose()
