# ADR-001: Why RAIC Exists

## Status
Accepted

## Context
Digital Rakshak utilizes multiple specialized AI models to process complex cyber threat cases. Initially, these models were invoked directly from API endpoints or tightly coupled service layers. This led to brittle execution logic, duplicated reasoning, and an inability to dynamically route or compose multi-step AI workflows.

## Decision
We introduce the **Rakshak AI Orchestrator (RAIC)**. RAIC acts as a first-class control plane separating business orchestration from raw AI inference. 

## Consequences
- **Decoupling:** API endpoints no longer know *how* AI executes, only that they requested an analysis.
- **Observability:** RAIC controls the execution graph, allowing us to emit standardized Server-Sent Events (SSE) across the entire pipeline.
- **Maintainability:** Adding a new agent requires registering it in RAIC, rather than modifying the core API router.
