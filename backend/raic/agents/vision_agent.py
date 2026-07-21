from shared.contracts.agent import IAgent
from shared.contracts.capability import ICapability
from shared.contexts.investigation import AgentContext
from shared.results.agent_result import AgentResult

class VisionAgent(IAgent):
    def __init__(self, capability: ICapability):
        self._capability = capability

    async def execute(self, context: AgentContext) -> AgentResult:
        evidence = context.evidence_target
        image_path = evidence.raw_data

        if not image_path:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=["No raw_data provided in EvidenceContext for VisionAgent"]
            )

        try:
            # Pass custom analyze type via metadata if present
            analyze_type = evidence.metadata.get("analyze_type", "scam")
            
            cap_result = await self._capability.invoke({
                "image_path": image_path,
                "analyze_type": analyze_type
            })
            
            return AgentResult(
                status="SUCCESS",
                confidence=cap_result.get("confidence", 0.0),
                execution_time_ms=cap_result.get("execution_time_ms", 0),
                findings=[cap_result["decision"]],
                evidence_links=cap_result["evidence"], 
                metadata=cap_result.get("metadata", {})
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=[f"VisionCapability execution failed: {str(e)}"]
            )
