from shared.contracts.agent import IAgent
from shared.contracts.capability import ICapability
from shared.contexts.investigation import AgentContext
from shared.results.agent_result import AgentResult

class CampaignAgent(IAgent):
    def __init__(self, capability: ICapability):
        self._capability = capability

    async def execute(self, context: AgentContext) -> AgentResult:
        evidence = context.evidence_target
        text = evidence.raw_data

        if not text:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=["No raw_data provided in EvidenceContext for CampaignAgent"]
            )

        try:
            cap_result = await self._capability.invoke({"text": text})
            
            return AgentResult(
                status="SUCCESS",
                confidence=cap_result["confidence"],
                execution_time_ms=cap_result["execution_time_ms"],
                findings=["Generated 384-dimensional vector embedding", "Vector similarity check completed."],
                evidence_links=cap_result["entities"], 
                metadata=cap_result["metadata"]
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=[f"CampaignCapability execution failed: {str(e)}"]
            )
