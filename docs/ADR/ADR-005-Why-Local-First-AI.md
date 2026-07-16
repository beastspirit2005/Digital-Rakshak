# ADR-005: Why Local-First AI

## Status
Accepted

## Context
Cyber Threat Intelligence deals with highly sensitive, personally identifiable information (PII) including bank statements, citizen voice recordings, and financial fraud data. Relying exclusively on third-party cloud APIs (like OpenAI or Anthropic) introduces unacceptable data privacy risks and latency dependencies.

## Decision
We prioritize **Local-First AI**. RIE runtimes are designed to execute optimized models (Qwen, Llama Vision, Whisper, MobileNetV3) natively on self-hosted infrastructure. 

## Consequences
- **Privacy:** Sensitive investigation data never leaves the Digital Rakshak cluster.
- **Cost:** Fixed infrastructure costs rather than unpredictable token pricing.
- **Performance:** Bypasses external network latency, though it shifts the burden to managing internal GPU VRAM (handled by RIE).
