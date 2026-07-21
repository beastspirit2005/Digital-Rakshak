import uuid
from raic.graph import ExecutionGraph, Stage, Parallelism, RetryPolicy, Priority
from shared.contexts.investigation import InvestigationContext
from raic.agent_registry import AgentRegistry

class ExecutionPlanner:
    """
    Responsible for knowing which agents should execute, when, and with what dependencies.
    Builds the immutable ExecutionGraph.
    """
    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    def plan(self, context: InvestigationContext) -> ExecutionGraph:
        """
        Creates an ExecutionGraph mapped to the pipeline stages.
        Pipeline: Validation -> Enrichment -> Classification -> Correlation -> Decision -> Reporting
        """
        graph_id = str(uuid.uuid4())
        
        # In a real system, the planner inspects the context to determine which agents to include.
        # Here we map out the default pipeline.
        
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
                agents=["threat_agent", "behaviour_agent", "vision_agent", "voice_agent"],
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
        
        # Filter agents to only those available in the registry, if we wanted to be robust
        # For this implementation, we assume the graph is statically defined or registry has them.
        
        return ExecutionGraph(
            graph_id=graph_id,
            pipeline_stages=stages
        )
