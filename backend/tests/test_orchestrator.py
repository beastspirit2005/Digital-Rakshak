import pytest
import asyncio
from backend.raic.orchestrator import RAICOrchestrator
from backend.raic.planner import ExecutionPlanner
from backend.raic.execution_engine import ExecutionEngine
from backend.raic.decision.fusion import EvidenceFusion
from backend.raic.decision.consensus import ConsensusEngine
from backend.raic.decision.calibration import ConfidenceCalibration
from backend.raic.decision.decision import DecisionEngine
from backend.raic.decision.explainability import ExplainabilityEngine
from backend.raic.agent_registry import AgentRegistry
from backend.shared.contexts.investigation import InvestigationContext
from backend.shared.events.investigation_events import InvestigationCreated, InvestigationClosed

class MockExecutionEngine(ExecutionEngine):
    async def execute(self, graph, investigation, state):
        # Mock execution that just populates AI results
        state.ai_results = {
            "threat_agent": {"confidence": 0.9, "threat_class": "PHISHING"}
        }
        state.update_status("COMPLETED_GRAPH")

@pytest.mark.asyncio
async def test_orchestrator_end_to_end():
    registry = AgentRegistry()
    planner = ExecutionPlanner(registry)
    engine = MockExecutionEngine(registry)
    fusion = EvidenceFusion()
    consensus = ConsensusEngine()
    calibration = ConfidenceCalibration()
    decision = DecisionEngine()
    explainability = ExplainabilityEngine()
    
    orchestrator = RAICOrchestrator(
        planner=planner,
        engine=engine,
        fusion=fusion,
        consensus=consensus,
        calibration=calibration,
        decision=decision,
        explainability=explainability
    )
    
    context = InvestigationContext(
        case_id="TEST-CASE-456",
        raw_text="Suspicious text here",
        evidence=[],
        runtime="test"
    )
    
    # Execute
    state = await orchestrator.execute_investigation(context)
    
    # Verify State
    assert state.case_id == "TEST-CASE-456"
    assert state.decision["decision"] == "TAKEDOWN_RECOMMENDED"
    assert len(state.recommendations) > 0
    assert "PHISHING" in state.recommendations[0]
    
    # Verify Events Emitted
    assert len(orchestrator.events) == 2
    assert isinstance(orchestrator.events[0], InvestigationCreated)
    assert isinstance(orchestrator.events[1], InvestigationClosed)
    assert orchestrator.events[1].final_status == "TAKEDOWN_RECOMMENDED"
