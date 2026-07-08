# Digital Rakshak — Design System (v1 draft, pending approval)

Direction: a calm, confident civic-intelligence product. Paper-warm light mode, green-charcoal
dark mode, one disciplined chartreuse accent. Derived from the `ui refs/` boards (Immediate,
CashPilot, Finzai, neobank lime cards) — editorial type, sage surfaces, lime used surgically.

---

## 1. Audit (2026-07-06)

**Stack:** Next.js 16.2.9 (App Router) · React 19 · Tailwind v4 (CSS-first `@theme`) ·
next-themes (class strategy) · framer-motion · Recharts · lucide-react · MapLibre GL ·
Cytoscape/force-graph · react-hook-form + zod · zustand auth store · axios via `lib/api.ts`.

**Current styling problems**
- Token layer is 10 generic shadcn-ish variables; everything else is raw Tailwind palette
  classes (`purple-500`, `blue-500`, `red-500`…) and hardcoded hex in charts (`#4f46e5`, `#ec4899`).
- `glass-panel` blur cards everywhere, indigo→purple gradient blobs, glow shadows,
  pure-near-black dark mode (`#09090b`) — all on the banned list.
- No type scale, no spacing discipline, ALL-CAPS CTAs ("SHOULD I TRUST THIS?"),
  icon-per-bullet feature grids, fake decorative heatmap dots.
- Almost no shared components: pages are 150–470-line monoliths with inline stat cards,
  tables, badges, and duplicated chart config.

**Pages (17 routes)**

| Route | Role | Notes |
|---|---|---|
| `/` | public | Landing/marketing |
| `/auth/login`, `/auth/register`, `/auth/reset-password` | public | Forms, OTP |
| `/citizen` | citizen | Personal dashboard |
| `/report` | all | Multi-step scam report wizard (470 lines) |
| `/prevention` | all | Prevention suite / education |
| `/copilot` | police/admin | AI chat + voice transcription |
| `/workbench` | police | Investigator dashboard (stats, trend, donut, cases table) |
| `/workbench/map` | all | MapLibre spatial map |
| `/workbench/graph` | police | Cytoscape graph explorer |
| `/workbench/reports` | police | FIR/TPR case table |
| `/banker` | banker | Nodal officer dashboard |
| `/admin` + `/users`, `/approvals`, `/intelligence`, `/ai-health`, `/settings` | admin | Console (6 pages) |

**Shared components (existing):** dashboard layout (sidebar + header), case-timeline,
global-chat-widget, network-visualizer, spatial-map, protected-route, theme-provider/toggle.
Everything else must be extracted into the new library.

**Data boundaries (frozen):** all fetching is client-side axios against `api(path)` with
Bearer token from `useAuthStore`. Response shapes (e.g. `cases[]` with `case_number`,
`scam_type_code`, `priority`, `status`, `city`, `state`) are treated as immutable contracts.

---

## 2. Color tokens

All colors are CSS custom properties on `:root` (light) and `.dark`, mapped into Tailwind v4
via `@theme inline`. **Zero raw hex in components.** next-themes keeps system-default +
manual override (already persisted in localStorage).

### Light — "paper"
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F3F1E9` | App background (warm cream) |
| `--surface` | `#FBFAF5` | Cards, panels |
| `--surface-2` | `#E9EADF` | Sidebar, insets, hover tint (muted sage) |
| `--surface-3` | `#DFE3D2` | Selected/active tint |
| `--ink` | `#1E2A23` | Primary text (green-charcoal) |
| `--ink-2` | `#5A665E` | Secondary text |
| `--ink-3` | `#8A948C` | Placeholder/disabled |
| `--line` | `#DCDCD0` | Hairline borders |
| `--accent` | `#B8E92E` | Chartreuse fills (always with `--accent-ink` text) |
| `--accent-ink` | `#182013` | Text on accent |
| `--accent-text` | `#4E7A0E` | Accent as text/icon on light bg (AA) |
| `--lilac` | `#A99BD4` | Secondary data series, tags |
| `--peach` | `#D98E70` | Negative deltas, secondary series |
| `--success` | `#3E7A48` | Semantic |
| `--warning` | `#9A6B1F` | Semantic |
| `--danger` | `#B2452F` | Semantic |

### Dark — "moss charcoal"
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#141813` | App background (green-charcoal, never #000) |
| `--surface` | `#1C211A` | Cards |
| `--surface-2` | `#242B22` | Lifted surfaces, sidebar |
| `--surface-3` | `#2D352A` | Active/hover |
| `--ink` | `rgba(242,241,232,.92)` | Body text |
| `--ink-2` | `#A3AC9E` | Secondary |
| `--ink-3` | `#6E7769` | Placeholder |
| `--line` | `#2E332B` | Borders |
| `--accent` | `#C6F24E` | Chartreuse fills |
| `--accent-ink` | `#161B10` | Text on accent |
| `--accent-text` | `#C6F24E` | Accent as text on dark (AA) |
| `--lilac` | `#BDAFE3` | Secondary series |
| `--peach` | `#E5A183` | Negative deltas |
| `--success` | `#8CC98F` | Semantic |
| `--warning` | `#D9B36A` | Semantic |
| `--danger` | `#E08A75` | Semantic |

Rules: lime is fills-only in light mode (`--accent-text` for the rare text case); max 2–3 lime
moments per viewport; priority/status badges use tinted surface + semantic text, not saturated
Tailwind colors.

## 3. Typography

- **Display / numbers:** `Archivo` variable (semi-condensed width ~92, weights 500–700),
  tight tracking, `font-variant-numeric: tabular-nums` on all stats/tables.
- **Body / UI:** `Instrument Sans` — clean grotesque with more character than Inter.
- **Editorial accent (sparing):** `Fraunces` — section eyebrows on landing + auth headline only.
- Loaded via `next/font/google` (self-hosted at build, no runtime calls).

Scale (tokens): `12 / 14 / 16 / 20 / 28 / 40 / 64` → `--text-xs … --text-display`.
No arbitrary sizes in components.

## 4. Spacing, radius, elevation, motion

- Spacing scale: 4/8/12/16/24/32/48/64.
- Radius: `--r-card: 12px`, `--r-control: 8px`, `--r-pill: 999px`. Nothing else.
- One shadow per theme: light `0 1px 2px rgb(30 42 35 / .06), 0 8px 24px rgb(30 42 35 / .05)`;
  dark relies on surface lift, shadow near-zero. Depth = surface tint, not shadow stacks.
- Motion tokens: `--ease-out: cubic-bezier(.22,1,.36,1)`, durations 150/200/250ms micro,
  400ms entrance; 40ms stagger. All gated behind `prefers-reduced-motion`.

**Signature moment — "the confidence dial":** on dashboard load, the hero metric's ring
draws in (stroke-dashoffset, 600ms) while its number ticks up with tabular figures.
It reappears in miniature on case rows (RAIC confidence). Everything else stays quiet.

## 5. Component library (`src/components/ui/`)

Button (primary=lime, secondary=surface, ghost, destructive) · Input/Textarea/Select ·
Card · StatBlock (w/ delta + optional dial) · ChartFrame (Recharts wrapper: no gridline noise,
token palette, draw-in once) · DataTable (desktop sticky-header table → mobile stacked cards) ·
Tabs (sliding indicator) · Modal/Sheet · Toast · Badge/Tag (pill) · Avatar · Skeleton
(layout-matched) · EmptyState · PageHeader · SidebarNav + MobileTabBar.

All interactive states (hover/active/focus-visible/disabled) defined at token level.

## 6. Migration order

1. Tokens + fonts + globals.css rewrite (`feat: token layer`)
2. UI primitives (`feat: component library`)
3. App shells: dashboard layout (sidebar/header/mobile tab bar), auth layout
4. Pages: auth → citizen → report wizard → workbench (+reports/map/graph) → banker →
   admin suite → copilot → prevention → landing
5. Motion pass (entrances, dial, counters, reduced-motion)
6. Responsive/QA pass at 375/768/1440, both themes, contrast check; screenshot self-critique

One commit per coherent step. Backend untouched; any backend-shaped idea goes to DESIGN_NOTES.md.
