from backend.shared.contracts.agent import IAgent
from backend.shared.contracts.capability import ICapability
from backend.shared.contexts.investigation import AgentContext
from backend.shared.results.agent_result import AgentResult

class VoiceAgent(IAgent):
    def __init__(self, capability: ICapability):
        self._capability = capability

    async def execute(self, context: AgentContext) -> AgentResult:
        evidence = context.evidence_target
        audio_path = evidence.raw_data

        if not audio_path:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=["No raw_data provided in EvidenceContext for VoiceAgent"]
            )

        try:
            cap_result = await self._capability.invoke({"audio_path": audio_path})
            
            return AgentResult(
                status="SUCCESS",
                confidence=cap_result["confidence"],
                execution_time_ms=cap_result["execution_time_ms"],
                findings=[cap_result["transcript"]],
                evidence_links=[], 
                metadata=cap_result["metadata"]
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=[f"VoiceCapability execution failed: {str(e)}"]
            )
