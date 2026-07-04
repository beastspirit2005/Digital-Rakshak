# ADR 005: Human Verification & Reinforcement Learning (RLHF)

## Status
Accepted

## Context
AI hallucinations or misclassifications in law enforcement software could lead to severe consequences (wrongful account freezes, missed threats). The platform must ensure accuracy while continuously learning from human experts.

## Decision
We enforce a **Human-in-the-Loop (HITL)** architecture for all critical actions (like freezing accounts or dispatching units). Furthermore, every human correction made via the Investigator Workbench acts as a Reinforcement Learning from Human Feedback (RLHF) signal.

## Rationale
1. **Accountability**: Legal frameworks demand that AI acts as an advisor, not the final adjudicator. A human investigator must press the final "Verify" button.
2. **Continuous Learning**: By capturing the delta between the AI's initial recommendation and the human's final verified state, we create structured reward/penalty datasets. This allows us to dynamically adjust Agent Consensus weights and fine-tune local models over time.
3. **Evidence Separations**: We strictly separate Immutable Evidence from Mutable Intelligence, ensuring that original source material is never altered by AI hallucinations, allowing for clean human review.

## Consequences
- **UX Complexity**: The frontend workbench must be complex enough to allow investigators to override specific fields (like specific OCR text or threat severity) cleanly.
- **Latency to Resolution**: Actions are delayed until human verification occurs, necessitating priority queues to ensure critical threats are reviewed first.
