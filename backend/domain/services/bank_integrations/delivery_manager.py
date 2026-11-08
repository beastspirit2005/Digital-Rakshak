import logging
from typing import Dict, Any, Optional, Tuple
from domain.models.bank import BankEscalation, BankRegistry
from domain.services.bank_integrations.base_adapter import BaseBankAdapter
from domain.services.bank_integrations.sandbox_adapter import SandboxBankAdapter
from domain.services.bank_integrations.circuit_breaker import BankCircuitBreaker

logger = logging.getLogger(__name__)


class DeliveryManager:
    """
    Manages institutional delivery routing, circuit breaking, adapter selection,
    and resilience against partner bank downtime.
    """

    def __init__(self):
        self.circuit_breaker = BankCircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60.0)
        self._adapters: Dict[str, BaseBankAdapter] = {
            "SANDBOX_API": SandboxBankAdapter(),
            "DIRECT_API": SandboxBankAdapter(),
        }

    def register_adapter(self, integration_type: str, adapter: BaseBankAdapter) -> None:
        self._adapters[integration_type] = adapter

    def get_adapter(self, integration_type: str) -> BaseBankAdapter:
        return self._adapters.get(integration_type, self._adapters["SANDBOX_API"])

    async def execute_delivery(
        self,
        escalation: BankEscalation,
        target_bank: BankRegistry
    ) -> Dict[str, Any]:
        """
        Executes alert delivery to target bank under circuit breaker supervision.
        """
        bank_code = target_bank.bank_code
        can_proceed, reason = self.circuit_breaker.can_execute(bank_code)

        if not can_proceed:
            logger.warning(f"Delivery to {bank_code} suppressed by circuit breaker: {reason}")
            raise ConnectionError(f"Circuit breaker active for {bank_code}: {reason}")

        adapter = self.get_adapter(target_bank.integration_type)

        try:
            result = await adapter.submit_alert(escalation, target_bank)
            self.circuit_breaker.record_success(bank_code)
            return result
        except Exception as e:
            self.circuit_breaker.record_failure(bank_code, str(e))
            raise e
