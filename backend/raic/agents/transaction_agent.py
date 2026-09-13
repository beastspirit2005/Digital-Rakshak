from shared.contracts.agent import IAgent
from shared.contexts.investigation import AgentContext
from shared.results.agent_result import AgentResult
from domain.agents.transaction_agent import TransactionAgent as DomainTransactionAgent


class TransactionAgent(IAgent):
    """
    RAIC Agent wrapper for Transaction Fraud Intelligence.
    Executes FeatureEngine, Attack DNA, Graph Ring detection, and Adaptive Friction.
    """
    def __init__(self, domain_agent: DomainTransactionAgent = None):
        self._agent = domain_agent or DomainTransactionAgent()

    async def execute(self, context: AgentContext) -> AgentResult:
        evidence = context.evidence_target
        txn_data = evidence.raw_data if isinstance(evidence.raw_data, dict) else {}

        if not txn_data:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=["No transaction raw_data provided in EvidenceContext for TransactionAgent"]
            )

        try:
            res = await self._agent.analyze_transaction(txn_data)
            
            return AgentResult(
                status="SUCCESS",
                confidence=res.get("confidence", 0.0),
                execution_time_ms=res.get("inference_time_ms", 0),
                findings=[
                    f"Decision: {res['decision']}",
                    f"Risk Band: {res['risk_band']} ({int(res['risk_score'] * 100)}%)",
                    f"Reason Codes: {', '.join(res['reason_codes'])}"
                ],
                evidence_links=[evidence.evidence_id],
                metadata=res
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                confidence=0.0,
                execution_time_ms=0,
                errors=[f"TransactionAgent execution failed: {str(e)}"]
            )

