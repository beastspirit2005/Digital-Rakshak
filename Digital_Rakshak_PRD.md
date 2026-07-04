# Digital Rakshak — Product Requirements Document (PRD)

**Version:** Hackathon Build v1.0
**Scope:** ET AI Hackathon 2026 — Round 2 Prototype
**Source:** Adapted from Digital Rakshak Project Proposal v2.0

---

## 1. Product Vision (One Line)

A platform where one citizen's scam report doesn't just get filed — it gets connected, in real time, to every other report that's part of the same fraud campaign, with a human investigator approving every step.

---

## 2. Problem We're Solving

- Fraud reports are handled as isolated incidents. The same scam gets "discovered" dozens of times because nothing links related complaints together.
- Citizens have no fast way to check if a message, call, or QR code is part of a known scam pattern before they act on it.
- Investigators manually re-type evidence from screenshots, calls, and documents into case forms — slow, repetitive, and error-prone.
- Existing systems are either fully manual (slow, human-only) or fully automated (risky, no accountability). Nothing in between.

---

## 3. What We're Building (Scope Statement)

**One end-to-end demonstrable story**, not the full national platform:

> A citizen submits a suspicious screenshot or QR code → AI extracts and analyzes it → the system finds it matches the "Attack DNA" of other recent reports → a graph reveals a connected fraud campaign → a human investigator reviews, corrects, and approves → the verified case enters the intelligence repository → the dashboard reflects national impact in real time.

This is the **full lifecycle in miniature**: Detect → Correlate → Verify → Learn. Not all 8 stages, not all 7 agents — one complete, working slice.

---

## 4. In Scope vs. Out of Scope

### In Scope (Build This)

| Component | What It Does |
|---|---|
| **Vision Intelligence Agent** | Detects scam patterns in screenshots, analyzes QR codes, flags counterfeit/suspicious visual content |
| **Behaviour Intelligence Agent ("Attack DNA")** | Compares scam script/text patterns against known cases using similarity matching — finds cases that "feel the same" even with different names/numbers |
| **Campaign Intelligence (lightweight)** | Groups matched cases into a "campaign" using shared indicators (phone prefix, UPI pattern, script similarity) |
| **Threat Confidence Engine** | Calculates a risk/confidence score from the above agents' outputs |
| **Human Verification Workbench** | The screen where an investigator reviews AI output, corrects mistakes, and approves/rejects |
| **National Threat Intelligence Repository (simplified)** | A Postgres-backed store of verified cases with "related cases" shown |
| **Citizen-facing reporting channel** | One channel only — WhatsApp bot or simple web form — for submitting reports and checking suspicious content |
| **Live impact dashboard** | Shows cases processed, campaigns detected, estimated fraud prevented (₹) |

### Out of Scope (Mock, Stub, or Roadmap Slide Only)

| Component | Treatment |
|---|---|
| Voice Intelligence Agent (speech-to-text, call analysis) | **Not built.** Mention as roadmap. |
| Geospatial Intelligence (live map, spread prediction) | **Mocked at most** — static map image or simple seeded animation if time allows in final week. Not a working agent. |
| Graph Intelligence Agent (full Neo4j network analysis) | **Simplified.** Represented as a relational join + simple force-directed visualization, not a full graph DB analytics layer, unless this becomes the headline feature and time allows. |
| Knowledge Intelligence Agent (RAG over regulations) | **Not built.** Roadmap only. |
| NCRP / CERT-In / Banks / NPCI / Telecom integrations | **Stub APIs only** — return fixed mock responses behind the real interface contract. Never actually called. |
| Multi-channel access (IVR, email, full mobile app) | **One channel only** for the demo (WhatsApp bot or web). Others are roadmap. |
| Bank/FI Officer & Policy Maker dashboards | **Not built.** Only Citizen + Investigator roles are demoed. |
| SLA escalation automation (Day 3/7/14) | **Not built.** Mentioned as a designed feature, not demoed live. |

---

## 5. User Roles (Demo Scope Only)

| Role | What They Do in the Demo |
|---|---|
| **Citizen** | Submits a screenshot/QR/message via the reporting channel, gets an instant preliminary read, sees their case status |
| **Investigation Officer** | Opens the Verification Workbench, reviews AI-extracted evidence + confidence score, corrects errors, approves or escalates the case |

*(Bank Officer, Cyber Cell, Administrator, Policy Maker roles exist in the full vision — Section 13 of the original proposal — but are not built for this prototype.)*

---

## 6. Core User Flows

### Flow A — Citizen Reports a Scam
1. Citizen sends a screenshot or message via WhatsApp bot (or web form)
2. Vision/Behaviour agent analyzes it within seconds
3. Citizen receives an instant preliminary verdict: risk level + plain-language explanation
4. Case is queued for human verification

### Flow B — Campaign Correlation (the "wow" moment)
1. New case comes in
2. System compares it against existing case database using similarity scoring (Attack DNA)
3. If matches found, system groups them into a campaign and visually shows the connection
4. Investigator sees: "This case is part of a 7-report campaign across 4 cities"

### Flow C — Human Verification
1. Investigator opens Workbench, sees AI's extracted evidence + confidence score + reasoning ("why" the AI flagged this)
2. Investigator can edit/correct any extracted field
3. Investigator approves → case enters National Threat Intelligence Repository
4. Investigator can also reject or escalate

### Flow D — Impact Dashboard
1. Real-time counters: cases processed, campaigns identified, estimated fraud amount prevented
2. Updates live as demo data is processed during the presentation

---

## 7. Success Criteria for the Demo

The prototype succeeds if, live in front of judges, it can:

1. Accept a real submitted screenshot/message and produce a sensible AI analysis (not a hardcoded response)
2. Show at least one genuine campaign correlation — a new case visibly linking to pre-seeded related cases
3. Let a judge or teammate act as the investigator and approve/correct a case through the Workbench UI
4. Reflect that approval in the dashboard/repository immediately
5. Ideally: let a judge submit something via the citizen channel (WhatsApp) themselves

---

## 8. Non-Functional Requirements

- **Explainability:** Every AI flag must show *why* (which indicators triggered it), not just a score
- **Human-in-the-loop is non-negotiable in the demo:** nothing reaches the repository without an approval click — this is the platform's core trust story, not a backend detail
- **Graceful degradation:** if any agent or external call fails or is slow, the system should show a clear "could not analyze" state rather than freezing or crashing the demo
- **No real PII processing:** use synthetic/seeded data only; no real personal data should be required to run the demo

---

## 9. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Trying to build too many agents | Scope locked to 2 working agents (Vision, Behaviour) + lightweight Campaign correlation. Everything else mocked. |
| No real fraud/bank/telecom data access | Use public OSINT examples + self-created synthetic seed dataset (~30 pre-built related cases) for the campaign correlation demo |
| Live demo failure (API timeout, model error) | Pre-test the exact demo script multiple times; have a recorded fallback video segment for the riskiest live step |
| Graph visualization scope creep | Default to a simple relational "related cases" list + force-directed JS visualization; only attempt full Neo4j integration if ahead of schedule |
