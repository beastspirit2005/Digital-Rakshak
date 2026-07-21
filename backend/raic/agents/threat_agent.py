from shared.contracts.agent import IAgent
from shared.contracts.capability import ICapability
from shared.contexts.investigation import AgentContext
from shared.results.agent_result import AgentResult

class ThreatAgent(IAgent):
    """
    RAIC Agent for analyzing raw text for cyber threats.
    Delegates inference to the injected ThreatCapability.
    """
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
                errors=["No raw_data provided in EvidenceContext for ThreatAgent"]
            )

        try:
            # Route to capability
            cap_result = await self._capability.invoke({"text": text})
            
            # Map into the standardized AgentResult
            return AgentResult(
                status="SUCCESS",
                confidence=cap_result.get("confidence", 0.0),
                execution_time_ms=cap_result.get("execution_time_ms", 0),
                findings=[f"Detected Threat Class: {cap_result['threat_class']}"],
                evidence_links=[evidence.evidence_id],
                metadata=cap_result.get("metadata", {})
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=[f"ThreatCapability execution failed: {str(e)}"]
            )
