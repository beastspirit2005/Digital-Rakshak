# ADR 003: Hybrid AI Routing (Google Gemini + Local Ollama)

## Status
Accepted

## Context
Digital Rakshak requires vast AI reasoning capabilities for tasks ranging from transcription to advanced threat consensus. Purely local execution of massive LLMs is constrained by the 8GB VRAM limit on the target hardware. Purely cloud execution raises privacy concerns regarding highly sensitive PII data.

## Decision
We will use a **Dual Gateway Hybrid Architecture**:
1. **Google Gemini API (Cloud)**: Handled via direct HTTP integration or the official SDK. Used for high-reasoning tasks, multimodal inputs (Vision OCR), and complex data fusions where data can be safely anonymized.
2. **Ollama + Mistral 7B (Local)**: Used as a fallback, and as the primary engine for privacy-sensitive tasks, basic embeddings, and the local AI Co-Pilot chat client.

## Rationale
1. **Privacy-first**: Local execution ensures sensitive data (like financial records or personal addresses) can be processed securely without hitting external servers.
2. **Performance/Cost**: Offloading multimodal and heavy-reasoning tasks to Gemini 2.0 Flash/Pro speeds up processing drastically compared to struggling on local hardware, while providing superior intelligence.
3. **Hardware Utilization**: Keeping the local model constrained to a quantized Mistral 7B fits perfectly within the RTX 5060's 8GB VRAM alongside OS overhead.

## Consequences
- **Routing Logic**: The system must intelligently route queries to the correct engine via a central Configuration Profile, which adds complexity to the Application Layer.
- **API Keys**: Relies on a valid Gemini API key securely managed in `.env`.
