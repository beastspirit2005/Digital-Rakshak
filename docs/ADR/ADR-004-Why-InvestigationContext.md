# ADR-004: Why InvestigationContext

## Status
Accepted

## Context
During the investigation lifecycle, functions were passing an unmanageable number of parameters (e.g., `execute_agent(case_id, evidence_list, prior_results, user_role, strict_mode)`). This parameter bloat caused brittle interfaces and made it difficult to inject new state data into downstream agents. 

However, creating a single "God Object" was recognized as a massive anti-pattern that leads to unmaintainable 3000-line contexts.

## Decision
We introduce **Composed Contexts**. The root `InvestigationContext` will act as a structural container holding smaller, strictly scoped contexts:
- `EvidenceContext`
- `RuntimeContext`
- `ExecutionContext`
- `InvestigationMetadata`

## Consequences
- **Cleaner APIs:** Functions accept a single `InvestigationContext` (or specific sub-contexts) instead of massive parameter lists.
- **Safety:** By avoiding a single God Object, we enforce strict domain boundaries (e.g., an OCR agent only requires the `EvidenceContext`, not the `RuntimeContext`).
