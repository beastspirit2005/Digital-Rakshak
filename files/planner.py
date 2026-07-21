import uuid
from raic.graph import ExecutionGraph, Stage, Parallelism, RetryPolicy, Priority
from shared.contexts.investigation import InvestigationContext
from raic.agent_registry import AgentRegistry


class ExecutionPlanner:
    """
    Responsible for knowing which agents should execute, when, and with what
    dependencies. Builds the immutable ExecutionGraph dynamically based on the
    InvestigationContext — skipping agents whose evidence type they can't handle.
    """
    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    def plan(self, context: InvestigationContext) -> ExecutionGraph:
        """
        Inspects the InvestigationContext to determine which agents to activate.
        Pipeline: Validation → Enrichment → Classification → Correlation → Decision → Reporting
        """
        graph_id = str(uuid.uuid4())

        # Determine evidence types present
        mime_types = {e.content_type for e in context.evidence}
        has_text  = any("text" in m for m in mime_types)
        has_image = any(m.startswith("image") for m in mime_types)
        has_audio = any("audio" in m for m in mime_types)

        # Classification agents — only include agents that match the evidence
        classification_agents = []
        if has_text:
            classification_agents.append("threat_agent")
            classification_agents.append("behaviour_agent")
        if has_image:
            classification_agents.append("vision_agent")
        if has_audio:
            classification_agents.append("voice_agent")

        # Fallback — always run at least threat + behaviour if no evidence typed
        if not classification_agents:
            classification_agents = ["threat_agent", "behaviour_agent"]

        stages = [
            Stage(
                stage_name="Validation",
                agents=["evidence_agent"],
                parallelism=Parallelism(max_concurrent=2, fail_fast=True),
                priority=Priority.HIGH
            ),
            Stage(
                stage_name="Enrichment",
                agents=["knowledge_agent"],
                parallelism=Parallelism(max_concurrent=5)
            ),
            Stage(
                stage_name="Classification",
                agents=classification_agents,
                parallelism=Parallelism(max_concurrent=10)
            ),
            Stage(
                stage_name="Correlation",
                agents=["campaign_agent"],
                parallelism=Parallelism(max_concurrent=3)
            ),
            Stage(
                stage_name="Decision",
                agents=["consensus_agent", "decision_agent"],
                priority=Priority.CRITICAL
            ),
            Stage(
                stage_name="Reporting",
                agents=["explainability_agent"],
                priority=Priority.LOW
            )
        ]

        return ExecutionGraph(
            graph_id=graph_id,
            pipeline_stages=stages
        )
