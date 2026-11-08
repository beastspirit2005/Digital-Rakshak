import time
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerState:
    CLOSED = "CLOSED"      # Normal operation: requests pass through
    OPEN = "OPEN"          # Tripped: requests fail fast to prevent cascade
    HALF_OPEN = "HALF_OPEN"# Trial probe after cooldown


class BankCircuitBreaker:
    """
    Per-Institution Circuit Breaker.
    Protects both Digital Rakshak and partner banking gateways from cascading failure loops.
    Trips to OPEN after consecutive failures; allows a controlled test probe in HALF_OPEN after cooldown.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        
        # State tracking per bank code: {bank_code: {"state": ..., "failures": ..., "last_failure_time": ...}}
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_entry(self, bank_code: str) -> Dict[str, Any]:
        if bank_code not in self._states:
            self._states[bank_code] = {
                "state": CircuitBreakerState.CLOSED,
                "consecutive_failures": 0,
                "last_failure_time": 0.0,
                "total_trips": 0,
                "last_error": None
            }
        return self._states[bank_code]

    def can_execute(self, bank_code: str) -> Tuple[bool, str]:
        """
        Determines whether requests to this bank can proceed.
        Returns: (can_proceed, status_reason)
        """
        entry = self._get_entry(bank_code)
        now = time.time()

        if entry["state"] == CircuitBreakerState.OPEN:
            # Check if cooldown period has elapsed
            if now - entry["last_failure_time"] >= self.recovery_timeout_seconds:
                entry["state"] = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker for bank {bank_code} transitioned to HALF_OPEN (probing).")
                return True, "Circuit breaker in HALF_OPEN trial mode"
            else:
                remaining = int(self.recovery_timeout_seconds - (now - entry["last_failure_time"]))
                return False, f"Circuit breaker OPEN for {bank_code}. Degraded; retrying in {remaining}s."

        return True, "Circuit breaker CLOSED (healthy)"

    def record_success(self, bank_code: str) -> None:
        """Records a successful response, resetting consecutive failure counts."""
        entry = self._get_entry(bank_code)
        if entry["state"] in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
            logger.info(f"Circuit breaker for bank {bank_code} recovered to CLOSED.")
        entry["state"] = CircuitBreakerState.CLOSED
        entry["consecutive_failures"] = 0
        entry["last_error"] = None

    def record_failure(self, bank_code: str, error_msg: str) -> None:
        """Records a dispatch failure, tripping to OPEN if threshold reached."""
        entry = self._get_entry(bank_code)
        entry["consecutive_failures"] += 1
        entry["last_failure_time"] = time.time()
        entry["last_error"] = error_msg

        if entry["consecutive_failures"] >= self.failure_threshold:
            entry["state"] = CircuitBreakerState.OPEN
            entry["total_trips"] += 1
            logger.critical(
                f"Circuit breaker TRIPPED to OPEN for bank {bank_code} "
                f"after {entry['consecutive_failures']} consecutive failures. Error: {error_msg}"
            )

    def get_health_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of all monitored institution circuit breaker states."""
        snapshot = {}
        for code, data in self._states.items():
            snapshot[code] = {
                "state": data["state"],
                "consecutive_failures": data["consecutive_failures"],
                "total_trips": data["total_trips"],
                "last_error": data["last_error"]
            }
        return snapshot

    def force_trip(self, bank_code: str, reason: str = "Manual test simulation") -> None:
        """Utility for failure injection and scenario testing."""
        entry = self._get_entry(bank_code)
        entry["state"] = CircuitBreakerState.OPEN
        entry["consecutive_failures"] = self.failure_threshold
        entry["last_failure_time"] = time.time()
        entry["total_trips"] += 1
        entry["last_error"] = reason

    def force_reset(self, bank_code: str) -> None:
        """Resets circuit breaker for a bank code."""
        entry = self._get_entry(bank_code)
        entry["state"] = CircuitBreakerState.CLOSED
        entry["consecutive_failures"] = 0
        entry["last_error"] = None
