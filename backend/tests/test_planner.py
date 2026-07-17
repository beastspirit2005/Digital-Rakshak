import pytest
from backend.raic.planner import ExecutionPlanner
from backend.raic.agent_registry import AgentRegistry
from backend.shared.contexts.investigation import InvestigationContext

def test_planner_topological_stages():
    registry = AgentRegistry()
    planner = ExecutionPlanner(registry)
    
    # Create mock context
    context = InvestigationContext(
        case_id="TEST-CASE-123",
        raw_text="Test phishing link",
        evidence=[],
        runtime="test"
    )
    
    # Generate graph
    graph = planner.plan(context)
    
    # Assert graph was created
    assert graph.graph_id is not None
    assert len(graph.pipeline_stages) == 6
    
    # Verify exact topological order
    expected_stages = ["Validation", "Enrichment", "Classification", "Correlation", "Decision", "Reporting"]
    actual_stages = [stage.stage_name for stage in graph.pipeline_stages]
    
    assert actual_stages == expected_stages
    
    # Verify some agent assignments
    classification_stage = graph.get_stage("Classification")
    assert "threat_agent" in classification_stage.agents
    assert classification_stage.parallelism.max_concurrent == 10
