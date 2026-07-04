# Digital Rakshak — Phase-by-Phase Feature Checklist

**Purpose:** One running checklist, organized by build phase (matches the Phase Build Plan). Each task is tagged with its owner so the team stays aligned on both *what's next* and *who's doing it*.

**Owner tags used below:**
- **[Backend/AI]** — Backend & AI Dev
- **[Frontend]** — Frontend/Full-Stack Dev (also supports backend integration where noted)
- **[Support A]** — Non-technical teammate — content, data, coordination
- **[Support B]** — Non-technical teammate — QA, logistics, submission

---

## Phase 0 — Setup & Validation (Days 1–3)

- [ ] Set up repo, environments, project scaffolding — backend **[Backend/AI]**
- [ ] Set up repo, environments, project scaffolding — frontend **[Frontend]**
- [ ] PostgreSQL setup and core schema design (cases, users, evidence, campaigns) **[Backend/AI]**
- [ ] Decide and lock the single citizen channel (WhatsApp bot vs. web form) **[Backend/AI + Frontend, joint decision]**
- [ ] Confirm core AI libraries/APIs work end-to-end with a trivial test call (LLM, OCR, etc.) **[Backend/AI]**
- [ ] Source 10–15 real, publicly available scam screenshots/messages as test inputs **[Support A]**
- [ ] Write the 30 synthetic seed case "scripts" — realistic scam message variations sharing underlying patterns (content only) **[Support A]**
- [ ] Set up the team's task tracker (this doc) and confirm everyone knows how to update it **[Support B]**
- [ ] Log the hackathon's full submission requirements and deadlines (prototype, deck, video, diagram) **[Support B]**

**Exit check:** A dummy request travels from the chosen citizen channel → backend → database and back.

---

## Phase 1 — Core Foundation (Days 4–8)

- [ ] Authentication / basic role check (citizen vs. investigator) **[Backend/AI]**
- [ ] Case data model fully implemented (case, evidence, status, confidence score, campaign link) **[Backend/AI]**
- [ ] Citizen reporting flow — channel-to-database plumbing, no AI yet **[Backend/AI]**
- [ ] Load the synthetic seed dataset into the database **[Backend/AI]**
- [ ] Citizen-facing reporting interface (form or chat UI) **[Frontend]**
- [ ] Investigator Workbench shell — case list view **[Frontend]**
- [ ] Investigator Workbench shell — basic case detail view (raw submitted evidence only) **[Frontend]**
- [ ] Dashboard shell — static counters wired to real (even if zero) DB counts **[Frontend]**
- [ ] Begin drafting user-facing copy: citizen instructions, Workbench labels **[Support A]**
- [ ] Begin compiling real public stats (RBI/NCRP/MHA figures) to ground the dashboard later **[Support A]**
- [ ] First manual click-through of the basic pipeline; log anything confusing **[Support B]**

**Exit check:** A citizen can submit something and an investigator can see it appear in a list.

---

## Phase 2 — Vision Intelligence Agent (Days 9–13)

- [ ] Build Vision Intelligence Agent — OCR extraction from screenshots/QR codes **[Backend/AI]**
- [ ] Build suspicious-indicator classification logic (urgency language, payment requests, fake branding cues) **[Backend/AI]**
- [ ] Structure agent output: extracted text + flagged indicators + confidence score + plain-language explanation **[Backend/AI]**
- [ ] API endpoint for case submission with Vision Agent analysis attached **[Backend/AI]**
- [ ] Wire Vision Agent output into citizen instant-verdict screen **[Frontend, supported by Backend/AI on integration]**
- [ ] Wire Vision Agent output into Investigator Workbench case detail view **[Frontend, supported by Backend/AI on integration]**
- [ ] Citizen instant-verdict screen UI (the result a citizen sees right after submitting) **[Frontend]**
- [ ] Test Vision Agent against the real sourced scam examples and log accuracy/issues **[Support A]**
- [ ] Write plain-language explanation copy templates for common flag types **[Support A]**

**Exit check:** Submit a real scam screenshot and get a sensible, non-hardcoded analysis visible in both citizen and investigator views.

---

## Phase 3 — Behaviour Intelligence Agent + Campaign Correlation (Days 14–19)

*(This phase contains the core demo "wow" — prioritize accordingly.)*

- [ ] Build Behaviour Intelligence Agent — text/script embedding generation **[Backend/AI]**
- [ ] Build similarity scoring against the seeded case database ("Attack DNA" matching) **[Backend/AI]**
- [ ] Build lightweight Campaign Correlation logic — group matched cases above a similarity threshold **[Backend/AI]**
- [ ] Build Threat Confidence Engine — combine Vision + Behaviour outputs into one unified score + explanation **[Backend/AI]**
- [ ] API endpoint for campaign lookup / related-cases retrieval **[Backend/AI]**
- [ ] Campaign correlation visualization — live "network reveal" (force-directed graph or equivalent) **[Frontend]**
- [ ] Attack DNA side-by-side comparison visual (two scam scripts, match % highlighted) **[Frontend]**
- [ ] Wire confidence/explanation data into the Workbench "why" panel **[Frontend, supported by Backend/AI on integration]**
- [ ] Review seed dataset to confirm campaign clusters are realistic and will visibly trigger correlation — adjust scripts if matches are too weak/strong **[Support A]**
- [ ] Run early end-to-end test of the correlation demo moment and log results **[Support B]**

**Exit check:** Submit a new case seeded to match existing campaign data — system correctly identifies and visually shows the connection live, not pre-scripted.

---

## Phase 4 — Human Verification Workbench (Days 20–23)

- [ ] Full Workbench review screen — evidence, confidence score, "why" reasoning panel, linked campaign info **[Frontend]**
- [ ] Editable fields — investigator can correct AI-extracted values **[Frontend]**
- [ ] Approve / Reject / Escalate actions with status updates **[Frontend, supported by Backend/AI on integration]**
- [ ] Backend logic: approved cases write into the simplified National Threat Intelligence Repository **[Backend/AI]**
- [ ] Backend logic: approved cases become available as "related cases" for future submissions **[Backend/AI]**
- [ ] Error handling & graceful degradation — clear "could not analyze" state if an agent call fails or times out **[Backend/AI]**
- [ ] Live impact dashboard — wire counters to real approval data (cases processed, campaigns detected, ₹ estimated prevented) **[Frontend]**
- [ ] Finalize ₹-prevented calculation logic using researched public stats **[Support A, figures; Backend/AI, implementation]**
- [ ] Full non-technical click-through of the Workbench — confirm it's understandable without explanation **[Support B]**
- [ ] Log every confusing label, broken state, or unclear flow found during testing **[Support B]**

**Exit check:** A non-technical teammate or judge can use the Workbench, correct a field, approve a case, and see the dashboard update immediately.

---

## Phase 5 — Polish, Wow Factors & Demo Rehearsal (Days 24–28)

- [ ] Implement live "money saved" counter animation **[Frontend]**
- [ ] Set up citizen channel for judges to test live (WhatsApp bot QR code or equivalent) **[Backend/AI + Frontend]**
- [ ] UI/UX consistency pass — styling, loading states, error states across all screens **[Frontend]**
- [ ] Stub/mock endpoints for external integrations (NCRP, CERT-In, Banks) behind real interface contracts, if time allows **[Backend/AI]**
- [ ] Final bug bash — run the full demo script repeatedly, fix anything that breaks **[Backend/AI + Frontend]**
- [ ] Write and finalize the exact demo script (who clicks what, in what order, with timing) **[Support A]**
- [ ] Prepare presentation slide deck content (problem, solution, architecture, roadmap, future scope) **[Support A]**
- [ ] Prepare "Future Scope" / Q&A talking points (what's mocked vs. real, and why) **[Support A]**
- [ ] Coordinate and run rehearsal sessions; track what breaks each run **[Support A + Support B]**
- [ ] Update architecture diagram to reflect what's actually built vs. mocked **[Support B, with input from both devs]**
- [ ] Coordinate demo video recording (script timing, screen capture, narration) **[Support B]**
- [ ] Prepare judge-facing one-pager / leave-behind summary **[Support B]**
- [ ] Time-keep rehearsals to confirm the demo fits the allotted slot **[Support B]**
- [ ] Compile and organize the final submission package ahead of deadline **[Support B]**

**Exit check:** The full demo flow (citizen submits → AI analyzes → campaign reveal → investigator approves → dashboard updates) runs successfully, start to finish, without manual intervention, at least 3 times in a row.

---

## Explicitly Out of Scope (Do Not Add Mid-Build)

Voice Intelligence Agent · full Geospatial map · full Neo4j Graph Agent · Knowledge/RAG Agent · real external integrations (NCRP/CERT-In/Banks/Telecom) · multi-channel access beyond one citizen channel · Bank Officer/Cyber Cell/Admin/Policy Maker dashboards · SLA escalation automation.

If any phase finishes early, only wow-factor polish (Phase 5 items) gets pulled forward — never new agents or new scope.

---

## How to Use This Doc

- Treat each phase's checklist as that week's sprint — don't start next phase's backend/AI items early; integration points depend on the previous phase being solid
- Update checkboxes daily; if a task is blocked, flag it immediately in standup rather than letting it sit silently
- Support A and Support B tasks are not filler — accurate content and honest QA from a non-technical perspective directly affect how judges experience the demo, same as the code does
