from typing import Dict, List
from shared.contracts.agent import IAgent
from shared.contexts.investigation import InvestigationContext
import logging

logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    RAIC Agent Registry.
    Dynamically stores all agent capabilities and orchestrates execution dependencies.
    """
    def __init__(self):
        self._agents: Dict[str, IAgent] = {}
        self._dependencies: Dict[str, List[str]] = {}

    def register(self, name: str, agent: IAgent, depends_on: List[str] = None):
        self._agents[name] = agent
        self._dependencies[name] = depends_on or []
        logger.info(f"Registered Agent: {name}")

    def get_execution_graph(self) -> List[List[str]]:
        """
        Calculates execution order using topological sort.
        Returns a list of stages, where each stage is a list of agents that can run in parallel.
        """
        resolved = []
        unresolved = set(self._agents.keys())
        stages = []
        
        while unresolved:
            stage = []
            for agent_name in list(unresolved):
                deps = self._dependencies.get(agent_name, [])
                if all(dep in resolved for dep in deps):
                    stage.append(agent_name)
                    
            if not stage:
                raise ValueError(f"Circular dependency detected in RAIC Agent Graph: {unresolved}")
                
            stages.append(stage)
            for agent_name in stage:
                resolved.append(agent_name)
                unresolved.remove(agent_name)
                
        return stages

    def get(self, name: str) -> IAgent:
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found in registry.")
        return self._agents[name]
