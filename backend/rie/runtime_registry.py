from typing import Dict, Type
from backend.shared.contracts.runtime import IRuntime
import logging

logger = logging.getLogger(__name__)

class RuntimeRegistry:
    """
    RIE Runtime Registry.
    Dynamically manages inference engines (PyTorch models, Llama, Whisper).
    """
    def __init__(self):
        self._runtimes: Dict[str, IRuntime] = {}

    def register(self, name: str, runtime: IRuntime):
        self._runtimes[name] = runtime
        logger.info(f"Registered Runtime: {name}")

    def get(self, name: str) -> IRuntime:
        if name not in self._runtimes:
            raise ValueError(f"Runtime '{name}' not found in registry.")
        return self._runtimes[name]

    def health_check(self) -> Dict[str, Any]:
        health = {}
        for name, runtime in self._runtimes.items():
            try:
                health[name] = runtime.health()
            except Exception as e:
                health[name] = {"status": "error", "message": str(e)}
        return health
