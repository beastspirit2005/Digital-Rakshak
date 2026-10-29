# Digital Rakshak — Refactoring & Sanitisation Changelog

**Release Milestone:** Refactoring & Sanitisation v1.0.0-rc1  
**Date:** 2026-10-29  
**Specification Reference:** CS-01 through CS-08

---

## 1. Summary of Changes

This changelog records all non-breaking architectural, security, performance, and hygiene refactorings applied across Digital Rakshak to meet the sanitisation objectives.

---

## 2. Detailed Modifications by Area

### 2.1 Repository Hygiene & Structural Cleanup (CS-01, CS-02)

- **Untracked Development & Credential Dumps:**
  - Removed git tracking and permanently purged local debug artifact files:
    - `backend/admin_sessions.txt`
    - `backend/users.txt`
    - `backend/api_test.txt`, `backend/api_test_2.txt`, `backend/api_test_admin.txt`
    - `backend/citizen_check.txt`
    - `backend/backend_tree.txt`
    - `frontend/frontend_log.txt`
    - `frontend/lint-results.txt`
    - `frontend/src/frontend_tree.txt`
    - `temp_val.txt`
  - Hardened `.gitignore` to prevent any future accidental staging of token dumps, local test outputs, or directory tree listings.

- **Reorganized Loose Backend Root Scripts:**
  - Created standardized directory `backend/scripts/manual_tests/` and moved developer verification scripts (`test_api.py`, `test_chat.py`, `test_connections.py`, `test_flow.py`, `test_graph.py`, `test_jwt.py`, `test_neo4j.py`, `test_otp.py`, `test_raic.py`, `test_submit.py`, `test_takedown.py`, `test_ws.py`, `integration_test.py`, `prod_e2e.py`).
  - Consolidated production and maintenance utilities into `backend/scripts/` (`seed_admin.py`, `seed_counterfeits.py`, `seed_data.py`, `seed_kb.py`, `setup_db.py`, `train_model.py`, `verify_blueprint.py`, `approve_admin.py`, `clean_neo4j.py`, `reanalyze_cases.py`, `sim_attack.py`, `inject_dummy_cases.py`, `inject_scams.py`).
  - Safely removed obsolete one-off debug scripts (`scratch_test.py`, `fix_last_null.py`, `fix_password.py`, `fix_db.py`, `fix_db_enum.py`, `fix_enum.py`, `check_db.py`, `check_cases.py`, `check_db_cases.py`, `clear_cases.py`, `get_otp.py`, `refactor_auth.py`).

---

### 2.2 Security & Authorization Hardening (CS-03)

- **Evidence Access Control Enforcement (BOLA / DPDP Act Compliance):**
  - **File:** `backend/api/v1/evidence.py`
  - **Change:** Hardened `_check_evidence_access` to strictly restrict users with role `banker` or `bank_employee` from viewing evidence unless the associated case's scam category is classified as financial fraud (`FIN`, `BANK`, `UPI`, `PAY`, `CARD`, `LOAN`, `INVEST`, `CRYPTO`, `MULE`, `FRAUD`, `TXN`).
  - Denies access with `403 Forbidden` for non-financial cases (e.g. cyber harassment, defamation, unauthorized access).
  - Ensured all three evidence retrieval and download endpoints await the coroutine consistently.

- **Investigator Case Co-Pilot Authorization (BFLA):**
  - **File:** `backend/api/v1/chat.py`
  - **Change:** Guarded `POST /api/v1/chat/{case_id}/chat` so that officers cannot invoke or query AI investigation insights on cases assigned to other officers unless they have the `admin` role.

---

### 2.3 Backend Performance & Bug Fixes (CS-04, CS-06, CS-07)

- **Fixed Latent NameError in `undertake_case`:**
  - **File:** `backend/api/v1/cases.py`
  - **Change:** Added `from sqlalchemy import select, or_` to line 6, resolving the latent `NameError: name 'or_' is not defined` when an officer undertook a case using its UUID identifier.

- **JSON / JSONB Mutation Dirty-Tracking:**
  - **Files:** `backend/runtime/sla_monitor_daemon.py`, `backend/api/v1/cases.py`
  - **Change:** Added `flag_modified(case, "timeline_events")` and `flag_modified(case, "attack_dna")` in the automated SLA monitor worker to guarantee that dictionary mutations are persisted to PostgreSQL upon `session.commit()`.

- **Serverless SLA Trigger Endpoint:**
  - **File:** `backend/api/v1/cases.py`
  - **Change:** Added authenticated endpoint `POST /api/v1/cases/sla/evaluate-cron` guarded by `x-cron-secret` matching `settings.SECRET_KEY` or requiring an `admin` session. Enables resilient SLA monitoring in serverless deployments without persistent background daemon tasks.

- **Bounded Event Bus Fallback Timeout:**
  - **File:** `backend/infrastructure/event_bus/redis_streams.py`
  - **Change:** Wrapped Redis ping with `await asyncio.wait_for(self._redis.ping(), timeout=0.5)`, preventing indefinite socket hangs in network-isolated environments or sandbox containers.

- **Pytest Conftest Event Loop Deadlock Removal:**
  - **File:** `backend/tests/conftest.py`
  - **Change:** Removed `autouse=True` on `cleanup_db_engine` fixture, preventing the async engine teardown from deadlocking synchronous unit tests on Windows.

---

### 2.4 Frontend Optimisation & UI Standardization (CS-02, CS-05)

- **Cascading Render Elimination:**
  - **File:** `frontend/src/components/ui/loading-overlay.tsx`
  - **Change:** Refactored state synchronization to adjust state during render rather than calling `setState` inside `useEffect`, eliminating `react-hooks/set-state-in-effect` warnings.
  - **File:** `frontend/src/hooks/use-transaction-stream.ts`
  - **Change:** Decoupled WebSocket state transitions from the mount effect, eliminating cascading renders on dashboard initialization.

- **Integrated `CaseStepper` Component:**
  - **Files:**
    - `frontend/src/app/(dashboard)/workbench/workspace/[case_number]/page.tsx`
    - `frontend/src/app/(dashboard)/citizen/page.tsx`
    - `frontend/src/app/(dashboard)/admin/tracker/page.tsx`
  - **Change:** Standardized the visual 4-step case lifecycle across citizen, investigator, and administrative portals.

---

## 3. Verification Summary

- **Algorithmic Suite:** 15/15 tests PASSED in 0.57s.
- **Security Suite:** 9/9 tests PASSED in 16.27s (including BOLA checks, SLA cron auth, and query generation).
- **Frontend Type Safety:** `npx tsc --noEmit` exited with 0 compilation errors.
- **Cascading Render Audit:** 0 `react-hooks/set-state-in-effect` warnings remaining.
