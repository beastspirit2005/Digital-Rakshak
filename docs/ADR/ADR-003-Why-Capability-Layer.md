# ADR-003: Why Capability Layer

## Status
Accepted

## Context
Agents were hardcoded to specific models (e.g., `ThreatAgent` explicitly calling Qwen, or `VoiceAgent` explicitly calling Whisper). If we wanted to swap Qwen for Llama 3, or Whisper for Google Cloud Speech, it required rewriting the agent's core logic.

## Decision
We introduce a **Capability Layer** acting as an abstraction between RAIC (Agents) and RIE (Runtimes).
`ThreatAgent` -> `ThreatCapability` -> `ReasoningRuntime`.

## Consequences
- **Interchangeability:** We can seamlessly swap or upgrade inference engines (e.g., from Qwen to a newer local model) without touching any business or agent logic.
- **Standardization:** Capabilities enforce strict Input/Output contracts (DTOs) that models must conform to.
