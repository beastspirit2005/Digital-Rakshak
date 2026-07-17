import asyncio
from typing import Dict, Any
from backend.core.logger import get_logger
from backend.shared.contexts.investigation import InvestigationContext, AgentContext
from backend.shared.contexts.execution_state import ExecutionState
from backend.raic.graph import ExecutionGraph
from backend.raic.agent_registry import AgentRegistry

logger = get_logger(__name__)

class ExecutionEngine:
    """
    Execution Engine.
    Knows HOW to execute the graph. Handles traversal, concurrency, and context construction.
    """
    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    async def execute(self, graph: ExecutionGraph, investigation: InvestigationContext, state: ExecutionState):
        """
        Walks the ExecutionGraph stage by stage.
        """
        logger.info("ExecutionEngine starting graph execution", graph_id=graph.graph_id, case_id=investigation.case_id)
        state.update_status("RUNNING")
        
        for stage in graph.pipeline_stages:
            logger.info("Executing Pipeline Stage", stage=stage.stage_name)
            state.current_stage = stage.stage_name
            
            # For each agent in the stage, we build its context and invoke it
            tasks = []
            agent_names = []
            
            for agent_name in stage.agents:
                try:
                    agent = self._registry.get(agent_name)
                    
                    agent_context = AgentContext(
                        investigation_id=investigation.case_id,
                        correlation_id=state.correlation_id,
                        evidence_target=investigation.evidence[0] if investigation.evidence else None,
                        runtime=investigation.runtime
                    )
                    
                    tasks.append(agent.execute(agent_context))
                    agent_names.append(agent_name)
                except ValueError as e:
                    logger.warning("Agent not found in registry, skipping", agent=agent_name, error=str(e))
            
            # We would use stage.parallelism here in a real bounded semaphore,
            # For now we use standard asyncio.gather
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for name, res in zip(agent_names, results):
                    if isinstance(res, Exception):
                        logger.error("Agent execution failed", agent=name, error=str(res))
                        state.add_error(f"[{name}] {str(res)}")
                    else:
                        state.ai_results[name] = res
                        logger.info("Agent completed", agent=name, result_status=res.status)
            
            state.completed_stages.append(stage.stage_name)
            
        logger.info("ExecutionEngine completed graph", graph_id=graph.graph_id)
        state.update_status("COMPLETED_GRAPH")
