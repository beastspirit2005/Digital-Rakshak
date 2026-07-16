import logging
import structlog
import contextvars
from typing import Any, Dict

# Context variables for structured logging
correlation_id_cv = contextvars.ContextVar("correlation_id", default=None)
investigation_id_cv = contextvars.ContextVar("investigation_id", default=None)
agent_cv = contextvars.ContextVar("agent", default=None)
stage_cv = contextvars.ContextVar("stage", default=None)
runtime_cv = contextvars.ContextVar("runtime", default=None)
latency_cv = contextvars.ContextVar("latency", default=None)
gpu_cv = contextvars.ContextVar("gpu", default=None)

def inject_contextvars(
    logger: logging.Logger, log_method: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Inject contextvars into the log event."""
    corr_id = correlation_id_cv.get()
    if corr_id:
        event_dict["correlation_id"] = corr_id
        
    inv_id = investigation_id_cv.get()
    if inv_id:
        event_dict["investigation_id"] = inv_id
        
    agent = agent_cv.get()
    if agent:
        event_dict["agent"] = agent
        
    stage = stage_cv.get()
    if stage:
        event_dict["stage"] = stage
        
    runtime = runtime_cv.get()
    if runtime:
        event_dict["runtime"] = runtime
        
    latency = latency_cv.get()
    if latency is not None:
        event_dict["latency"] = latency
        
    gpu = gpu_cv.get()
    if gpu:
        event_dict["gpu"] = gpu
        
    return event_dict


def setup_logger():
    """Configure structlog for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            inject_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            inject_contextvars,
        ],
        processor=structlog.processors.JSONRenderer(),
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

def get_logger(name: str):
    return structlog.get_logger(name)

# Ensure setup is called on import
setup_logger()
