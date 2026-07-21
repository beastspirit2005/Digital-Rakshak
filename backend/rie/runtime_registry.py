from typing import Dict, Any, Type
from shared.contracts.runtime import IRuntime
from shared.contracts.engine import IEngine
from core.logger import get_logger

logger = get_logger(__name__)

class RuntimeRegistry:
    """
    RIE Runtime & Engine Registry.
    Dynamically manages inference runtimes (PyTorch models, Llama, Whisper)
    and Domain Engines that utilize them.
    """
    def __init__(self):
        self._runtimes: Dict[str, IRuntime] = {}
        self._engines: Dict[str, IEngine] = {}

    def register_runtime(self, name: str, runtime: IRuntime):
        self._runtimes[name] = runtime
        logger.info("Registered Runtime", runtime=name)

    def register_engine(self, name: str, engine: IEngine):
        self._engines[name] = engine
        logger.info("Registered Engine", engine_name=name)

    def get_runtime(self, name: str) -> IRuntime:
        if name not in self._runtimes:
            raise ValueError(f"Runtime '{name}' not found in registry.")
        return self._runtimes[name]

    def get_engine(self, name: str) -> IEngine:
        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found in registry.")
        return self._engines[name]

    def health_check(self) -> Dict[str, Any]:
        health = {"runtimes": {}, "engines": list(self._engines.keys())}
        for name, runtime in self._runtimes.items():
            try:
                health["runtimes"][name] = runtime.health()
            except Exception as e:
                health["runtimes"][name] = {"status": "error", "message": str(e)}
        return health
