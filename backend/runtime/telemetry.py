import psutil
import platform
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RuntimeTelemetry:
    """
    Monitors hardware health (CPU/RAM/GPU) and AI model latency.
    Used by the RIE Command Center to detect bottlenecks or GPU OOM conditions.
    """
    
    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Returns baseline host metrics."""
        health = {
            "os": platform.system(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": psutil.virtual_memory().percent,
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
        }
        return health
        
    @staticmethod
    def get_gpu_health() -> List[Dict[str, Any]]:
        """
        Attempts to read NVIDIA GPU VRAM metrics via NVML or nvidia-smi.
        If unavailable, falls back to CPU mock metrics for development.
        """
        gpu_stats = []
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                name = pynvml.nvmlDeviceGetName(handle)
                # Decode byte strings depending on pynvml version
                name_str = name.decode('utf-8') if isinstance(name, bytes) else str(name)
                
                gpu_stats.append({
                    "device_id": i,
                    "name": name_str,
                    "vram_total_mb": info.total // 1024**2,
                    "vram_used_mb": info.used // 1024**2,
                    "vram_percent": round((info.used / info.total) * 100, 1)
                })
        except Exception as e:
            logger.debug(f"GPU Telemetry unavailable (NVML failure): {e}")
            # Fallback for local development without GPUs
            gpu_stats = [{
                "device_id": 0,
                "name": "Local CPU (Mocked GPU)",
                "vram_total_mb": 16384,
                "vram_used_mb": 4096,
                "vram_percent": 25.0
            }]
            
        return gpu_stats
