"""
Synthetic agents for pipeline stages handled by the Decision Core directly.
These stubs ensure the ExecutionEngine doesn't log ValueError for missing agents
in the Validation, Enrichment, Decision, and Reporting stages.
"""
from shared.contracts.agent import IAgent
from shared.contexts.investigation import AgentContext
from shared.results.agent_result import AgentResult
import time


class NoOpAgent(IAgent):
    """
    A pass-through agent that completes instantly with a neutral result.
    Used for pipeline stages whose logic is handled by the Orchestrator's
    Decision Core directly (consensus, decision, explainability) or for
    stages that delegate to external processes (validation, knowledge).
    """
    def __init__(self, name: str):
        self._name = name

    async def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            status="SUCCESS",
            confidence=1.0,
            execution_time_ms=0,
            findings=[f"{self._name}: delegated to Decision Core"],
            evidence_links=[],
            metadata={"type": "no_op", "agent": self._name}
        )
