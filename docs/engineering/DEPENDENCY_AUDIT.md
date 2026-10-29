# Digital Rakshak — Third-Party Dependency & Vulnerability Audit

**Document ID:** DR-ENG-DEP-01  
**Audit Date:** 2026-10-29  
**Auditor:** Antigravity Engineering (Automated Baseline Audit)  
**Related Objectives:** CS-01 (Repository Hygiene), CS-03 (Security), CS-07 (Reliability)

---

## 1. Overview & Audit Scope

This audit reviews third-party libraries across the backend Python environment (`requirements.txt`) and frontend JavaScript ecosystem (`package.json`), assessing license compatibility, security advisory status, deprecation risks, and unnecessary or redundant packages.

---

## 2. Backend Dependencies (`backend/requirements.txt`)

### 2.1 Package Inventory & Security Status

| Package | Pinned Range | Category | Purpose | Security / Risk Assessment |
|:---|:---:|:---|:---|:---|
| `fastapi` | `>=0.100.0` | Core Web | API Routing & OpenAPI schema | Secure. Async ASGI framework. |
| `uvicorn[standard]` | `>=0.23.0` | Server | Production ASGI Server | Secure. Standard HTTP/1.1 & WebSockets. |
| `pydantic` | `>=2.0.0` | Validation | Data modeling & schema contracts | V2 Rust-core; zero known CVEs in current release. |
| `pydantic-settings`| `>=2.0.0` | Configuration | Environment variable loading | Compliant with 12-factor app design. |
| `sqlalchemy` | `>=2.0.0` | ORM | Database queries & unit-of-work | V2 async session mode. |
| `asyncpg` | `>=0.29.0` | Driver | Async PostgreSQL driver | High-performance binary protocol driver. |
| `psycopg2-binary` | `>=2.9.0` | Driver | Synchronous fallback driver | Required for synchronous Alembic migrations. |
| `pgvector` | `>=0.2.0` | Vectors | Vector embeddings & similarity | Supports pgvector PostgreSQL extension. |
| `alembic` | `>=1.11.0` | Migrations | Relational schema migrations | Maintained. |
| `neo4j` | `>=5.10.0` | Graph DB | Fraud syndicate & mule network graph | Async driver for Neo4j Aura/Enterprise. |
| `python-jose` | `>=3.3.0` | Cryptography | JWT token signing & decode | Uses `cryptography` backend for Ed25519/RSA. |
| `passlib[bcrypt]` | `>=1.7.4` | Auth | Secure password hashing | Standard 12-round bcrypt hashing. |
| `cryptography` | `>=41.0.0` | Security | Low-level cryptographic primitives | Constant-time comparisons and AES-GCM. |
| `httpx` | `>=0.25.0` | HTTP Client | Asynchronous external API calls | Used for OSINT and WhatsApp integrations. |
| `slowapi` | `>=0.1.9` | Security | Redis/memory rate limiting | Protects `/auth/login` and `/auth/register`. |
| `filetype` | `>=1.2.0` | Security | Magic byte MIME-type verification | Enforces real binary file headers for evidence. |
| `redis[asyncio]` | `>=5.0.0` | Streaming | Redis Streams transaction ingestion | Async connection pool with in-memory fallback. |
| `razorpay` | `>=1.4.1` | Payments | B2B enterprise tier billing | Official Razorpay Python SDK. |
| `reportlab` | `>=4.0.0` | Reporting | FIR / Evidence Dossier PDF export | Compliant for offline PDF rendering. |

### 2.2 Backend Observations & Hygiene Recommendations
- **`androguard` (Android APK Analysis):** Currently pinned at `>=3.4.0a1`. This package is large (~40MB) and used for mobile malware reverse engineering. Ensure sandboxed container limits memory allocation to 1GB during APK decompression to prevent zip-bomb exhaustion attacks.
- **`psycopg2-binary`:** Kept exclusively for Alembic migrations; all runtime API queries use `asyncpg`.

---

## 3. Frontend Dependencies (`frontend/package.json`)

### 3.1 Framework & Core Libraries

| Package | Version | Purpose | Assessment |
|:---|:---:|:---|:---|
| `next` | `16.2.9` | Core App Framework (App Router) | Active, production SSR & SSG. |
| `react` / `react-dom`| `19.2.4` | UI Framework | React 19 canary/latest with modern compiler support. |
| `typescript` | `^5` | Type Checker | Clean build verified (`tsc --noEmit` -> 0 errors). |
| `tailwindcss` | `^4` | Styling Engine | V4 with PostCSS. Fast CSS compilation. |
| `lucide-react` | `^1.23.0` | Icons | Tree-shakeable SVG icon set. |
| `zustand` | `^5.0.14` | Global State Store | Lightweight, zero-boilerplate client state. |
| `react-hook-form` | `^7.80.0` | Form Management | Uncontrolled inputs for minimal re-renders. |
| `zod` | `^4.4.3` | Schema Validation | Client-side form & API payload validation. |
| `axios` | `^1.18.1` | HTTP Client | Standardized API client (`@/lib/api`). |

### 3.2 Visualization & Graph Dependencies

| Package | Purpose | Assessment |
|:---|:---|:---|
| `cytoscape` & `react-cytoscapejs` | Graph layout and money-trail visualization | Robust canvas-based renderer for complex fraud rings. |
| `react-force-graph-2d` & `force-graph` | 2D physics-based transaction network visualizer | WebGL / Canvas accelerated. Dynamically imported. |
| `maplibre-gl` & `react-map-gl` | Vector tile interactive map rendering | High performance, open-source alternative to Mapbox. |
| `recharts` | Dashboard statistics & analytics charts | SVG chart library for admin/bank metrics. |

---

## 4. Duplicate & Obsolete Package Audit

1. **No Duplicate UI Frameworks:** Project cleanly uses Tailwind CSS exclusively without conflicting component libraries (no mixing of Bootstrap or Chakra).
2. **State Store Consolidation:** Global state is strictly managed through Zustand (`useAuthStore`); no obsolete Redux or MobX dependencies present.
3. **No Stale Mocks in Production Builds:** Mock APIs are cleanly segregated under `backend/api/v1/mock_apis.py` and gated behind development environment configurations.
