import asyncio
import logging
from typing import Dict, Any, List
from backend.shared.contexts.investigation import InvestigationContext, AgentContext
from backend.shared.results.agent_result import AgentResult
from backend.raic.agent_registry import AgentRegistry
from backend.rie.runtimes.reasoning_runtime import RakshakReasoningRuntime

logger = logging.getLogger(__name__)

class RAICOrchestrator:
    """
    The heart of the v3 Architecture.
    Takes an InvestigationContext, resolves agent dependencies, executes them concurrently in stages,
    and uses the ReasoningRuntime to fuse their outputs into a final calibrated intelligence summary.
    """
    def __init__(self, agent_registry: AgentRegistry, reasoning_runtime: RakshakReasoningRuntime):
        self._registry = agent_registry
        self._reasoning = reasoning_runtime

    async def execute_investigation(self, investigation: InvestigationContext) -> InvestigationContext:
        """
        Executes the entire multi-agent pipeline based on the provided investigation context.
        """
        logger.info(f"Starting Investigation: {investigation.case_id}")
        
        # Determine Execution Graph
        try:
            stages = self._registry.get_execution_graph()
        except ValueError as e:
            logger.error(str(e))
            investigation.metadata.current_status = "FAILED"
            return investigation

        all_results: Dict[str, AgentResult] = {}
        
        # Execute Agents by Topological Stage
        for stage_idx, stage in enumerate(stages):
            logger.info(f"Executing Stage {stage_idx + 1}: {stage}")
            
            tasks = []
            agent_names = []
            
            for agent_name in stage:
                agent = self._registry.get(agent_name)
                # Build localized AgentContext
                agent_context = AgentContext(
                    investigation_id=investigation.case_id,
                    evidence_target=investigation.evidence[0] if investigation.evidence else None, # Simplified for now
                    runtime=investigation.runtime
                )
                tasks.append(agent.execute(agent_context))
                agent_names.append(agent_name)
                
            # Run stage concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, res in zip(agent_names, results):
                if isinstance(res, Exception):
                    logger.error(f"Agent {name} threw unhandled exception: {res}")
                elif isinstance(res, AgentResult):
                    all_results[name] = res
                    
        # AI Fusion via Reasoning Runtime
        await self._fuse_results(investigation, all_results)
        return investigation

    async def _fuse_results(self, investigation: InvestigationContext, results: Dict[str, AgentResult]):
        """
        Mathematical fusion of confidence and LLM synthesis of the final intelligence report.
        """
        valid_probs = [res.confidence for res in results.values() if res.status == "SUCCESS"]
        
        if not valid_probs:
            investigation.metadata.confidence_score = 0.0
            return
            
        # Independent probability fusion
        inv_prod = 1.0
        for p in valid_probs:
            inv_prod *= (1.0 - p)
            
        fused_confidence = 1.0 - inv_prod
        investigation.metadata.confidence_score = min(max(fused_confidence, 0.0), 0.99)
        investigation.metadata.current_status = "COMPLETED"
        
        # Here we would invoke self._reasoning.infer(...) to build the final English explanation.
        # To minimize code for this iteration, we map it back to the metadata.
        investigation.metadata.tags.extend([name for name in results.keys()])
