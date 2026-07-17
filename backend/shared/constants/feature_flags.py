import os
from enum import Enum
from typing import List

class DeploymentProfile(Enum):
    DEMO = "demo"               # Uses lightweight mock models
    CLOUD = "cloud"             # Uses Groq/OpenAI APIs
    AIRGAPPED = "airgapped"     # Uses Local Ollama/vLLM only, no internet

class FeatureFlags:
    """
    Centralized toggles for dynamically routing behavior based on the deployment profile.
    Critical for switching between cloud scalability and strict on-prem government security.
    """
    
    def __init__(self):
        self.profile = DeploymentProfile(os.getenv("DEPLOYMENT_PROFILE", "cloud").lower())
        
    @property
    def allow_external_api_calls(self) -> bool:
        """Determines if the system is allowed to make internet calls."""
        return self.profile != DeploymentProfile.AIRGAPPED
        
    @property
    def use_local_gpu_inference(self) -> bool:
        """Forces local GPU inference even if cloud is available."""
        return self.profile == DeploymentProfile.AIRGAPPED
        
    @property
    def enable_background_workers(self) -> bool:
        """In demo mode, we run synchronously to avoid queue complexity."""
        return self.profile != DeploymentProfile.DEMO

    @property
    def active_flags(self) -> List[str]:
        flags = [f"PROFILE_{self.profile.name}"]
        if self.allow_external_api_calls: flags.append("EXTERNAL_APIS_ENABLED")
        if self.use_local_gpu_inference: flags.append("LOCAL_GPU_FORCED")
        if self.enable_background_workers: flags.append("ASYNC_WORKERS_ENABLED")
        return flags

# Global flag instance
flags = FeatureFlags()
