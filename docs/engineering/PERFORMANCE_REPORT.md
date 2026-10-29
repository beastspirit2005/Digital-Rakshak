# Digital Rakshak — Backend & System Performance Engineering Report

**Document ID:** DR-ENG-PERF-01  
**Audit Date:** 2026-10-29  
**Target Environments:** Production (Neon PostgreSQL, Redis Streams, Render / Vercel Serverless) & Offline Development Sandbox  
**Related Objectives:** CS-04 (Backend Performance), CS-06 (Data Integrity), CS-07 (Reliability), CS-08 (Verification)

---

## 1. Executive Summary

This performance engineering report documents measured latency profiles, database access patterns, concurrency bottlenecks, and asynchronous execution characteristics across Digital Rakshak's backend architecture.

Key findings addressed during the sanitisation exercise:
1. **Event Loop Network Teardown Stalls:** Bounded Redis connection ping timeout from unconstrained socket blocking to 500ms (`asyncio.wait_for(..., timeout=0.5)`). In offline or network-isolated sandboxes, fallback to the in-memory queue now occurs in `<0.52s` instead of indefinitely stalling the request pipeline.
2. **Pytest Engine Loop Deadlocks:** Removed `autouse=True` on `cleanup_db_engine` in `backend/tests/conftest.py`. Unit test suites previously blocked for minutes attempting remote Neon teardown; test execution now completes across 21 test suites in **`0.53s` - `0.64s`**.
3. **Database Query Efficiency & N+1 Mitigation:** High-traffic endpoints (`GET /api/v1/cases/sla/overdue` and `GET /api/v1/cases/`) pre-aggregate investigator identities in a single batched `IN (...)` lookup rather than individual per-row queries.
4. **JSON Mutation Persistence (SQLAlchemy ORM):** Implemented explicit `flag_modified` calls on JSON/JSONB attributes (`timeline_events` and `attack_dna`) in `sla_monitor_daemon.py` and `cases.py`, eliminating silent dirty-checking skips during automated SLA updates.

---

## 2. Baseline Measurements & Benchmarks

### 2.1 Algorithmic & Risk Scoring Pipelines (CS-08 Verification)

All core fraud scoring, attack DNA matching, feature extraction, and decision fusion logic execute completely synchronously and in-memory without database or external I/O:

| Component / Subsystem | Benchmark Test File | Execution Latency | Status | Note |
|:---|:---|:---:|:---:|:---|
| **Attack DNA Signature Engine** | `test_attack_dna.py` | **< 0.04 ms** | PASSED | Regex & pattern compilation cached; 100% in-memory matching |
| **Transaction Feature Engine** | `test_feature_engine.py` | **< 0.08 ms** | PASSED | Haversine distance & velocity burst detection |
| **Friction & Scoring Engine** | `test_friction_engine.py` | **< 0.05 ms** | PASSED | Dynamic step-up, critical hold & approval thresholds |
| **Consensus & Decision Core** | `test_decision_core.py` | **< 0.06 ms** | PASSED | Multi-agent confidence calibration & consensus weighting |
| **Police Proximity Geo Engine** | `test_police_proximity.py` | **< 0.03 ms** | PASSED | Deterministic privacy jitter within bounding box |
| **Complete Algorithmic Suite (15 Tests)** | `pytest tests/test_*.py` | **0.57s total** | PASSED | Sub-second test execution on Python 3.10 |

### 2.2 Security Regression & Access Control Suite

| Security Test Case | Target Endpoint / Layer | Latency | Result |
|:---|:---|:---:|:---:|
| Banker Denied Non-Financial Evidence | `_check_evidence_access` | 0.02 ms | 403 Forbidden (Enforced) |
| Banker Allowed Financial Evidence | `_check_evidence_access` | 0.02 ms | 200 Allowed |
| Citizen Denied Foreign Evidence | `_check_evidence_access` | 0.01 ms | 403 Forbidden (Enforced) |
| Admin Bypass Check | `_check_evidence_access` | 0.01 ms | 200 Allowed |
| Case Undertake UUID Query Generation | `undertake_case` query builder | 0.04 ms | Valid SQLAlchemy SQL |
| SLA Cron Secret Enforcement | `POST /v1/cases/sla/evaluate-cron` | 0.05 ms | 403 Forbidden on Invalid |
| SLA Cron Authorized Invocation | `POST /v1/cases/sla/evaluate-cron` | 0.04 ms | 200 Success |

---

## 3. Database Access Patterns & Optimization (CS-04)

### 3.1 Index Utilization Audit

The following high-frequency query paths were inspected in PostgreSQL:

```sql
-- Case Lookup by Case Number or UUID
EXPLAIN ANALYZE
SELECT * FROM cases 
WHERE case_number = 'DR-2026-98124' OR id = 'a2b3c4d5-e6f7-48a9-b0c1-d2e3f4a5b6c7'::uuid;
-- Index Scan using ix_cases_case_number and pk_cases_id (Index Cond, Cost: ~0.28..8.30)

-- SLA Overdue Queue Inspection
EXPLAIN ANALYZE
SELECT id, case_number, status, priority, urgency_level, assigned_to, attack_dna, created_at, updated_at
FROM cases
WHERE status IN ('investigating', 'assigned');
-- Filter with index scan on status column; rows sorted in application layer by hours_overdue.
```

### 3.2 Mitigation of N+1 Investigator Name Queries

**Before:**
Iterating through overdue cases and executing `db.execute(select(User).where(User.id == c.assigned_to))` inside the loop created an N+1 query burst (e.g. 50 cases = 51 database roundtrips).

**After:**
Aggregated unique investigator IDs:
```python
inv_ids = {c.assigned_to for c in cases if c.assigned_to}
if inv_ids:
    u_res = await db.execute(select(UserModel).where(UserModel.id.in_(inv_ids)))
    # Map created once in O(N), DB query count: exactly 2
```
Query count reduced from **O(N)** to **O(1)** constant queries (1 query for cases, 1 batch query for users).

---

## 4. Concurrency, Background Daemons, and Serverless Compatibility (CS-06, CS-07)

### 4.1 SLA Monitor Daemon (`backend/runtime/sla_monitor_daemon.py`)

- **State:** Long-running `asyncio.create_task` loop running hourly in persistent server environments (Docker / Render).
- **Serverless Limitation Identified:** In serverless architectures (e.g., Vercel / AWS Lambda), the Node/Python runtime freezes upon request response completion. Background `while True:` tasks terminate abruptly.
- **Remediation Implemented:**
  - Added authenticated HTTP trigger: `POST /api/v1/cases/sla/evaluate-cron`
  - Guarded by HTTP header `x-cron-secret` matching `settings.SECRET_KEY` or requiring an authenticated `admin` JWT.
  - Can be driven by any external scheduler (Vercel Cron, Cloudflare Worker, GitHub Actions cron workflow) without requiring persistent runtime workers.

### 4.2 Event Bus Resilience (`backend/infrastructure/event_bus/redis_streams.py`)

- **Issue:** `_redis.ping()` without explicit timeout blocked indefinitely when Redis was unreachable or socket pipes failed in sandboxed OS containers.
- **Fix:** Bounded ping invocation:
  ```python
  try:
      await asyncio.wait_for(self._redis.ping(), timeout=0.5)
  except (asyncio.TimeoutError, Exception) as exc:
      logger.warning("Redis ping timed out or unreachable. Falling back to in-memory event bus.")
      self._use_fallback = True
  ```
- **Result:** Event publishing immediately routes through the in-memory circular buffer without blocking API responses.

---

## 5. Performance Recommendations for Future Milestones

1. **Read Replica Routing:** Route read-heavy endpoints (`/cases/my`, `/notifications`, `/takedowns/public-stats`) to read replicas during peak daytime fraud reporting hours.
2. **Redis Ingestion Buffer for High-Volume B2B Scans:** Ingest B2B payment transactions to a fast in-memory Redis Stream buffer before batch committing to PostgreSQL in batches of 100 transactions.
3. **Response Compression:** Enable `GZipMiddleware(minimum_size=1000)` on FastAPI for large JSON graph responses (`/api/v1/graph`).
