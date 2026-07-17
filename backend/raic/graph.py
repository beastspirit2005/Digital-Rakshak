from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_delay_ms: int = 100

class Dependency(BaseModel):
    agent_id: str
    required: bool = True

class Parallelism(BaseModel):
    max_concurrent: int = 5
    fail_fast: bool = False

class Stage(BaseModel):
    stage_name: str
    agents: List[str] = Field(default_factory=list)
    dependencies: List[Dependency] = Field(default_factory=list)
    parallelism: Parallelism = Field(default_factory=Parallelism)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    priority: Priority = Priority.NORMAL

class ExecutionGraph(BaseModel):
    """
    Immutable representation of the planned execution sequence.
    """
    graph_id: str
    pipeline_stages: List[Stage] = Field(default_factory=list)
    
    def get_stage(self, stage_name: str) -> Optional[Stage]:
        for stage in self.pipeline_stages:
            if stage.stage_name == stage_name:
                return stage
        return None
