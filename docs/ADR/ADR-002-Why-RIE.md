# ADR-002: Why RIE is Separate

## Status
Accepted

## Context
As the project evolved, AI inference (running PyTorch models, parsing LLM outputs, calling Whisper) became entangled with agent execution logic. When an agent needed to classify a threat, it directly initialized a model in memory.

## Decision
We separate inference out into the **Rakshak Intelligence Engine (RIE)**. RIE exclusively handles hardware acceleration (GPU/VRAM management), model loading, inference lifecycle, and health checks.

## Consequences
- **Scalability:** RIE can be independently scaled or deployed to dedicated GPU nodes while RAIC remains on lightweight CPU instances.
- **Clarity:** Agents no longer contain PyTorch imports.
- **Observability:** RIE provides dedicated endpoints for GPU health and inference latency.
