# Digital Rakshak — Phase-by-Phase Build Plan

**Timeline:** 4 weeks
**Scope:** Per PRD — 2 working AI agents, lightweight campaign correlation, human verification workbench, one citizen channel, live dashboard

---

## Phase 0 — Setup & Validation (Days 1–3)

**Goal:** Confirm the plan is buildable before writing feature code.

- Set up repo, environments, and basic project scaffolding (frontend + backend skeleton)
- Set up PostgreSQL instance and core schema (cases, users, evidence, campaigns)
- Collect/construct the synthetic seed dataset: ~30 fake-but-realistic scam reports with deliberately shared indicators (same script template, same UPI handle pattern, same phone prefix family) across multiple "cities," so campaign correlation has something real to find
- Decide and lock the single citizen channel (WhatsApp Business API vs. simple web form) — do not build both
- Confirm core libraries/APIs work end-to-end with a trivial "hello world" call (LLM call, OCR call, etc.) before building real features on top

**Exit check:** Can a dummy request travel from the chosen citizen channel → backend → database and back? If yes, proceed.

---

## Phase 1 — Core Foundation (Days 4–8)

**Goal:** The skeleton every other feature plugs into.

- Authentication (citizen vs. investigator login — can be simple role-based, not full RBAC)
- Case data model fully implemented: case record, evidence attachments, status, confidence score, linked-campaign field
- Citizen reporting flow (channel → case created in DB), no AI yet — just plumbing
- Basic Investigator Workbench shell (list of cases, click into a case, see raw submitted evidence)
- Basic dashboard shell (static counters wired to real DB counts, even if zero)

**Exit check:** A citizen can submit something and an investigator can see it appear in a list. No intelligence yet — just the pipe.

---

## Phase 2 — Vision Intelligence Agent (Days 9–13)

**Goal:** First real AI capability — screenshot/QR analysis.

- Build the Vision Intelligence Agent: takes an uploaded screenshot/QR, extracts text (OCR), classifies suspicious indicators (urgency language, payment requests, fake branding cues)
- Returns a structured output: extracted text, flagged indicators, confidence score, plain-language explanation
- Wire this into the citizen flow: submission → Vision Agent runs → citizen gets instant preliminary verdict
- Wire output into the Investigator Workbench: investigator sees the extracted evidence + confidence + reasoning

**Exit check:** Submit a real scam screenshot (publicly sourced example) and get a sensible, non-hardcoded analysis back, visible in both citizen and investigator views.

---

## Phase 3 — Behaviour Intelligence Agent + Campaign Correlation (Days 14–19)

**Goal:** The "wow" feature — Attack DNA matching and campaign reveal.

- Build the Behaviour Intelligence Agent: takes scam text/script content, generates a similarity embedding, compares against the seeded case database
- Build the lightweight Campaign Intelligence layer: if similarity exceeds a threshold across multiple cases, group them as a "campaign" with a shared ID
- Build the correlation visualization: when a new matching case comes in, show it connecting live to the existing campaign (this is the core demo moment — see wow factor doc)
- Threat Confidence Engine: combine Vision + Behaviour outputs into one unified confidence/risk score with explanation

**Exit check:** Submit a new case that's seeded to match existing campaign data → system correctly identifies and visually shows the connection, live, not pre-scripted.

---

## Phase 4 — Human Verification Workbench (Days 20–23)

**Goal:** Make the trust story real and interactive.

- Full Investigator Workbench UI: review extracted evidence, confidence score, reasoning ("why" panel), and linked campaign info
- Editable fields — investigator can correct any AI-extracted value before approving
- Approve / Reject / Escalate actions, each changing case status accordingly
- Approved cases write into the (simplified) National Threat Intelligence Repository view, and become visible as "related cases" for future submissions
- Wire dashboard counters to update live based on real approvals (cases processed, campaigns detected, estimated ₹ prevented)

**Exit check:** A non-technical teammate or judge can sit at the Workbench, understand what they're looking at without explanation, correct a field, and approve a case — and immediately see the dashboard update.

---

## Phase 5 — Polish, Wow Factors & Demo Rehearsal (Days 24–28)

**Goal:** Turn working features into a memorable, reliable demo.

- Add the agreed wow factors (per separate Wow Factor doc): live Network Reveal animation, judges-test-it-live channel, Attack DNA side-by-side match visual, live money-saved counter
- UI/UX pass: consistent styling, loading states, error states (graceful failure messaging if an agent call is slow/fails)
- Write and rehearse the exact demo script end-to-end, multiple times, with timing
- Prepare one pre-recorded fallback clip for the riskiest live step (in case live demo fails on stage)
- Prepare the architecture diagram, slide deck, and "Future Scope" slide covering everything mocked/out of scope (Voice Agent, full Graph DB, real external integrations, multi-channel access, other roles)
- Final bug bash — run the full demo script 5+ times back to back, fix anything that breaks

**Exit check:** The full demo flow (citizen submits → AI analyzes → campaign reveal → investigator approves → dashboard updates) runs successfully, start to finish, without manual intervention, at least 3 times in a row.

---

## What's Explicitly NOT Being Built (Repeated From PRD — Do Not Scope-Creep Into These)

- Voice Intelligence Agent
- Full Geospatial Intelligence / live map
- Full Neo4j Graph Intelligence Agent (only a simplified visual representation)
- Knowledge Intelligence Agent (RAG over regulations)
- Any real NCRP / CERT-In / Bank / NPCI / Telecom integration (stubs only, and only if time allows even building the stub)
- Multi-channel access beyond the one chosen citizen channel
- Bank Officer, Cyber Cell, Administrator, Policy Maker dashboards
- SLA escalation automation

If ahead of schedule in Phase 5, the *only* acceptable additions are wow-factor polish items — not new agents or new scope.
