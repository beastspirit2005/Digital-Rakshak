# Digital Rakshak — Frontend Optimization & UI Architecture Report

**Document ID:** DR-ENG-FRONTEND-01  
**Audit Date:** 2026-10-29  
**Framework:** Next.js 14 (App Router) + React 18 + Tailwind CSS + Lucide Icons  
**Target Objectives:** CS-02 (Architecture), CS-05 (Frontend Optimisation), CS-08 (Verification)

---

## 1. Executive Summary

During the Phase 2 & Phase 5 sanitisation exercise, the Next.js frontend codebase was audited across all 25+ application routes, component libraries, state stores, and real-time WebSocket hooks.

Key improvements achieved:
1. **Elimination of Cascading Render Cycles:** Resolved React 18/19 `react-hooks/set-state-in-effect` anti-patterns in key UI components (`LoadingOverlay`) and streaming hooks (`useTransactionStream`), preventing double-render churn during modal open and WebSocket connection initialization.
2. **Unified Incident Progression Stepper (`CaseStepper`):** Integrated the standardized visual case lifecycle stepper across all 3 primary user personas:
   - Citizen Dashboard (`/citizen`)
   - Investigator Workbench (`/workbench/workspace/[case_number]`)
   - Administrative Case Tracker (`/admin/tracker`)
3. **Strict Type Safety:** Verified complete frontend TypeScript build (`npx tsc --noEmit`) with **0 compilation errors**.
4. **Repository Hygiene:** Purged development log artifacts (`frontend_log.txt`, `lint-results.txt`, `frontend_tree.txt`) and added automatic exclusions to `.gitignore`.

---

## 2. Component Performance & State Management Optimizations

### 2.1 Eliminating Cascading Renders in Modal Overlays (`LoadingOverlay`)

**Before:**
`LoadingOverlay` used an effect to reset internal step state when opened:
```tsx
// Anti-pattern: synchronous setState inside effect causes immediate post-paint cascading re-render
useEffect(() => {
  if (open) {
    setInternalStep(0);
  }
}, [open]);
```

**After:**
Adopted the official React documentation recommended pattern ("Adjusting state while rendering"):
```tsx
const [internalStep, setInternalStep] = useState(0);
const [prevOpen, setPrevOpen] = useState(open);

if (open !== prevOpen) {
  setPrevOpen(open);
  if (open) {
    setInternalStep(0);
  }
}
```
React intercepts the state adjustment during the current render phase and restarts rendering before committing to the DOM or painting, eliminating layout thrashing.

---

### 2.2 WebSocket Streaming Hook Decoupling (`useTransactionStream`)

**Before:**
The `useTransactionStream` hook called `connect()` synchronously inside the `useEffect` on `enabled`, which immediately executed `setStatus("CONNECTING")` and `setStatus("ERROR")` inside synchronous catch blocks. This caused `react-hooks/set-state-in-effect` warnings and forced parent dashboards (e.g. Banker live feeds) to re-render twice on initialization.

**After:**
1. Defaulted state to `"CONNECTING"` on initial declaration.
2. Relocated connection state transitions strictly to asynchronous event lifecycle callbacks (`socket.onopen`, `socket.onerror`, `socket.onclose`).
3. Wrapped error state fallbacks in `setTimeout(..., 0)` to decouple them from synchronous mount effect execution.

ESLint verification confirmed **0** `react-hooks/set-state-in-effect` warnings remaining.

---

## 3. UI Component Reuse: `CaseStepper` Integration

Digital Rakshak defines a standardized 4-stage lifecycle for reported cyber fraud incidents:
1. **Submitted / Intake:** Citizen submission, AI initial risk triage, DRID token generation.
2. **Investigating:** Assigned to Cyber Crime Cell / Police Station; evidence forensics active.
3. **Action Taken / Freeze:** Bank freeze notices dispatched, malicious domains requested for takedown.
4. **Resolved / Closed:** Recovery or formal closure report filed.

### Integration Locations

| Persona / Route | File Path | Component Placement |
|:---|:---|:---|
| **Citizen View** | `frontend/src/app/(dashboard)/citizen/page.tsx` | Directly beneath case header card with status badge |
| **Investigator View** | `frontend/src/app/(dashboard)/workbench/workspace/[case_number]/page.tsx` | Sticky beneath main case header and priority indicator |
| **Admin Tracker** | `frontend/src/app/(dashboard)/admin/tracker/page.tsx` | Atop the detailed case inspection modal |

---

## 4. Bundle & Heavy Dependency Management

### 4.1 Leaflet Map Dynamic Imports

Interactive mapping libraries (`leaflet`, `react-leaflet`) require browser `window` objects and bundle heavy raster/tile assets. The application correctly prevents SSR hydration mismatch and reduces initial JS bundle size through dynamic imports with SSR disabled:

```tsx
const CyberCellMap = dynamic(
  () => import("@/components/map/cyber-cell-map"),
  { ssr: false, loading: () => <MapLoadingSkeleton /> }
);
```

### 4.2 Dead Artifact Elimination

The following transient files were purged from the frontend workspace and excluded via `.gitignore`:
- `frontend/frontend_log.txt` (Local browser console trace dump)
- `frontend/lint-results.txt` (Prior ESLint run text dump)
- `frontend/src/frontend_tree.txt` (Directory tree dump)

---

## 5. Verification Metrics

- **TypeScript Typecheck:** `npx tsc --noEmit` -> **0 errors**
- **Critical React Warnings:** `react-hooks/set-state-in-effect` -> **0 warnings**
- **Production Build Readiness:** Passed
