import uuid
from core.logger import get_logger
from shared.contexts.investigation import InvestigationContext
from shared.contexts.execution_state import ExecutionState
from raic.planner import ExecutionPlanner
from raic.execution_engine import ExecutionEngine
from raic.decision.fusion import EvidenceFusion
from raic.decision.consensus import ConsensusEngine
from raic.decision.calibration import ConfidenceCalibration
from raic.decision.decision import DecisionEngine
from raic.decision.explainability import ExplainabilityEngine
from shared.events.investigation_events import InvestigationCreated, InvestigationClosed

logger = get_logger(__name__)

class RAICOrchestrator:
    """
    The orchestrator acts as the coordinator.
    Delegates to the ExecutionPlanner to build the graph, the ExecutionEngine to traverse it,
    and the Decision Core to fuse results. Emits Domain Events.
    """
    def __init__(
        self, 
        planner: ExecutionPlanner, 
        engine: ExecutionEngine,
        fusion: EvidenceFusion,
        consensus: ConsensusEngine,
        calibration: ConfidenceCalibration,
        decision: DecisionEngine,
        explainability: ExplainabilityEngine
    ):
        self._planner = planner
        self._engine = engine
        self._fusion = fusion
        self._consensus = consensus
        self._calibration = calibration
        self._decision = decision
        self._explainability = explainability
        
        # Simple event bus mock
        self.events = []

    def _emit(self, event):
        self.events.append(event)
        logger.info("Emitted Domain Event", event_type=event.__class__.__name__, event_id=event.event_id)

    async def execute_investigation(self, investigation: InvestigationContext, on_agent_event=None) -> ExecutionState:
        """
        Executes the entire multi-agent pipeline based on the provided investigation context.
        """
        logger.info("Starting Investigation Orchestration", case_id=investigation.case_id)
        
        # Initialize execution state
        state = ExecutionState(
            case_id=investigation.case_id,
            correlation_id=str(uuid.uuid4())
        )
        
        self._emit(InvestigationCreated(
            event_id=str(uuid.uuid4()),
            correlation_id=state.correlation_id,
            case_id=investigation.case_id,
            triggered_by="API"
        ))
        
        # Determine Execution Graph
        graph = self._planner.plan(investigation)
        
        # Execute Pipeline
        await self._engine.execute(graph, investigation, state, on_agent_event=on_agent_event)
        
        if on_agent_event:
            await on_agent_event(investigation.case_id, "DecisionCore", "Running...", message="Calculating 6-factor consensus weights...")
        
        # Decision Core Processing
        # 1. Fuse evidence
        fused_data = self._fusion.fuse(state)
        
        # 2. Consensus
        consensus_data = self._consensus.determine_consensus(state)
        
        # 3. Calibration
        state.confidence_score = self._calibration.calibrate(state)
        
        # 4. Decision
        decision_data = self._decision.make_decision(state)
        state.decision = decision_data
        
        # 5. Explainability
        explanation = self._explainability.generate_explanation(state, decision_data)
        state.recommendations.append(explanation)
        
        self._emit(InvestigationClosed(
            event_id=str(uuid.uuid4()),
            correlation_id=state.correlation_id,
            case_id=investigation.case_id,
            final_status=decision_data["decision"]
        ))
        
        if on_agent_event:
            await on_agent_event(investigation.case_id, "DecisionCore", "Completed", confidence=state.confidence_score)
        
        return state
