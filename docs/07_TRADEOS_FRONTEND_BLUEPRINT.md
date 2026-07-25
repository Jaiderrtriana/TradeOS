# TRADEOS_FRONTEND_BLUEPRINT.md

**Document Status:** CANONICAL AND FROZEN — the official frontend implementation blueprint of TradeOS.
**Version:** 1.1
**Last Updated:** 2026-07-24
**Depends On:** all six prior frozen documents (`PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`, `TRADEOS_API_SPECIFICATION.md`). This document redesigns nothing — it translates the already-approved architecture and API contract into what a frontend engineer (human or AI) needs to build the UI without making an architectural decision of their own.
**Is Not:** React/Next.js code, component implementations, or a visual design file. It contains enough structure that building one should be a translation exercise, not a design exercise.
**Relationship to the prior UI prototype (`TradeOS_UI_v3`):** a 21-page static prototype was built earlier, before the six foundational documents existed. Where its pages and patterns match what those documents now confirm, this blueprint says so. Where the prototype invented something with no grounding in any frozen document (a search bar wired to nothing, a Watchlist page, a Risk Management page, Assets/Tags modules) it is **not** carried forward here — it is either re-derived from a confirmed capability or explicitly registered as an Open Question (Section 20). The prototype is a visual reference for feel, never a source of business truth.

---

## 1. Frontend Principles

1. **Single Source of Truth.** Every business fact and every computed value (`r_multiple`, Evaluation scores, Win Rate, Expectancy) comes from the API (`TRADEOS_API_SPECIFICATION.md`). The frontend never recomputes, caches-as-truth, or silently duplicates a calculation the backend already owns — this is the direct frontend-side enforcement of `TRADEOS_DOMAIN_MODEL.md`'s Domain Invariants, which say nothing about who is allowed to violate them by recomputing a derived value differently.
2. **Smart Backend, Thin Frontend.** The frontend's job is to collect input, display what the API returns, and route the user between screens. It contains no Evaluation Engine logic, no Domain Invariant checks used as the *authoritative* gate (client-side validation exists only for fast feedback — the API's own layered validation, `TRADEOS_API_SPECIFICATION.md` Section 9, remains the real authority), and no independent scoring or statistics math.
3. **Reusable Components.** A UI pattern is built once (Section 7) and reused everywhere it recurs — a second, slightly different table or card implementation for the same concept is a defect, not a variant.
4. **Accessibility First.** Not a pass applied at the end (Section 15) — every component in Section 7 is specified with its accessible behavior as part of its definition, not as an afterthought.
5. **Responsive by Default.** Every page (Section 5) is specified for at least desktop and mobile viewports; a page that only works at desktop width is incomplete, not "mobile-optimization deferred."
6. **Consistency Over Creativity.** The same filter bar, the same pagination control, the same error banner appear identically across every module — a novel one-off pattern for a single page is only justified if that page's business capability is genuinely unlike anything else, which is rare.
7. **Progressive Disclosure.** Complexity is available, never forced. The clearest example already confirmed by the API (`POST /trades`, `TRADEOS_API_SPECIFICATION.md` Section 6.4): `checklist_answers` and most classification fields are optional — the frontend must offer a "Simple" path that asks for only the required fields, and a "Pro" path that surfaces everything the API accepts, never only the maximal form.
8. **Optimistic UI Only Where Appropriate.** Because every write in v1 is synchronous and returns its final state in one round trip (`TRADEOS_API_SPECIFICATION.md` Section 10, no Long Running Operations), optimistic UI is rarely *necessary* — it is used only for low-stakes, easily-reversible interactions (e.g., toggling a UI-only filter), never for a Trade write, where the real response (including its computed Evaluation) is worth the wait rather than guessing it client-side.

---

## 2. Frontend Architecture

### 2.1 Overall Architecture
A single-page application consuming the versioned REST API (`TRADEOS_API_SPECIFICATION.md` Section 3) exclusively. There is no direct database access, no server-rendered business logic, and no secondary backend — every business fact the UI shows or writes passes through `/api/v1/...`.

### 2.2 Application Layers
```
Pages (Section 5)  →  Feature modules (Section 3)  →  API client layer  →  /api/v1/...
      ↑                                                        │
      └──────────────── reusable components (Section 7) ──────┘
```
The **API client layer** is the only code permitted to know an endpoint's URL, method, and payload shape (`TRADEOS_API_SPECIFICATION.md` Sections 6, 8). No component or page constructs a request manually — this is what lets a `v1 → v2` migration (`TRADEOS_API_SPECIFICATION.md` Section 12) touch one layer instead of every page that happens to call that endpoint.

### 2.3 Routing Strategy
One route per Page (Section 5), with nested routes for sub-resources exactly mirroring the API's own resource nesting (`TRADEOS_API_SPECIFICATION.md` Section 3.3) — e.g., a Trade Detail route nests naturally under a Trades route, echoing `/trades/{id}` echoing `/api/v1/trades/{id}`. Route parameters map 1:1 to API path parameters; no route encodes information the API doesn't also use to identify the same resource.

### 2.4 Feature Organization / Folder Philosophy
**Feature-first, mirroring the backend's module-first organization** (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3, ADR-02) — one top-level frontend folder per API module (Section 3 of this document), each containing its own pages, its own feature-specific components, and its own slice of the API client layer. Cross-feature reuse goes through Section 7's shared component library, never through one feature importing another feature's internals directly — the same "module boundaries are contracts" discipline the backend applies to itself (`TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 2), applied to the frontend.

### 2.5 State Management Philosophy
Two kinds of state, never conflated:
- **Server state** — anything that came from or will be sent to the API (a Trade, a list of Catalog entries, Statistics). Always fetched through the API client layer, always treated as *possibly stale* the moment it's received, never hand-edited in place to simulate a write's effect (Principle 8, Section 1).
- **UI state** — things with no backend meaning at all (is a modal open, which tab is active, an unsubmitted form's current draft values). Lives local to the component or feature that needs it and is never persisted through the API unless a form's own submission is what the user asked for.

### 2.6 Data Fetching Philosophy
Every read goes through the API client layer's typed methods, respecting the API's own filtering/sorting/pagination contract exactly (`TRADEOS_API_SPECIFICATION.md` Section 7) — the frontend never re-implements sorting or filtering over an already-fetched page of results, since that would silently diverge from what a second page of results would have shown under the same filter.

### 2.7 Caching Philosophy
Mirrors the API's own stance (`TRADEOS_API_SPECIFICATION.md` Section 15): Configuration and Catalog reads are safe to cache client-side for short periods (they change rarely); Trades, Statistics, and Evaluation reads are treated as fresh-on-every-view — refetched on navigation to the page that needs them, never assumed still valid from a prior visit, consistent with Domain Invariant DI-11's "Analytics never becomes a source of truth" applying equally to a client-side cache pretending to be one.

### 2.8 Error Handling Philosophy
Every API error is the standard envelope (`TRADEOS_API_SPECIFICATION.md` Section 8). The frontend has exactly one error-handling path per error category (Section 17) — never a bespoke `try/catch` per page inventing its own message for the same `code`.

### 2.9 Loading Strategy
Every page and every data-dependent component declares its Loading state explicitly (Section 5, Section 13) using a skeleton matching that content's eventual shape (Section 7) — never a generic spinner for a data table that will render as rows.

### 2.10 Empty States
Every list-shaped page (Trades, Journal, Catalogs, Playbook) has a defined empty state (Section 5) that explains *why* it's empty and what to do next (e.g., "No trades yet — log your first one") — never a bare blank table.

### 2.11 Offline Behavior
**No frozen document specifies offline behavior for TradeOS.** The API is synchronous, stateless, and assumes connectivity (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9). This blueprint does not invent an offline mode — registered as **Open Question FE-1** (Section 20). The only behavior specified here is the minimum: a clear "you appear to be offline" state distinct from a generic network error (Section 17), not a synchronization strategy.

### 2.12 Future Scalability
Because the API client layer is the sole owner of endpoint knowledge (Section 2.2) and features are organized to mirror Bounded Contexts (Section 2.4) exactly as the backend does, adding a new API module (Section 3) or migrating a resource to `/api/v2/...` (`TRADEOS_API_SPECIFICATION.md` Section 12) touches one feature folder and its client layer — never a cross-cutting rewrite.

---

## 3. Application Structure

Each module below corresponds 1:1 to an API Module (`TRADEOS_API_SPECIFICATION.md` Section 5), which itself corresponds 1:1 to a Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 4) — the same boundary, enforced a third time.

| Frontend Module | Responsibility | API Module | Confirmed? |
|---|---|---|---|
| **Authentication** | Login, registration, session bootstrap | Authentication | Yes |
| **Dashboard** | One composed overview screen | Dashboard (composition only) | Yes |
| **Trading** | Trade list, detail, entry, amendment, closure, mistake tagging | Trades | Yes |
| **Evaluation** | Score preview, historical Rule Explorer | Evaluation | Yes |
| **Configuration** | Scoring criteria/weights/versions/profiles, catalogs | Configuration, Catalogs | Yes |
| **Playbook** | Setup documentation and live performance | Playbook | Yes |
| **Mistakes** | Frequency/cost/priority ranking | Mistakes | Yes |
| **Statistics** | Overview, by-dimension, rolling analytics | Statistics | Yes |
| **Journal** | Trade-scoped and period-scoped reflection | Journal | Yes |
| **Settings** | Account, preferences | Users, Preferences | Yes |
| **Reports, Calendar, AI, Notifications, Trading Accounts** | Named in the prompt for this document | *(no confirmed API module)* | **Not confirmed** — see Section 20, and `TRADEOS_API_SPECIFICATION.md` Section 18 (API-4, API-5, API-6) |

**On the prior prototype:** `TradeOS_UI_v3` additionally included Watchlist, Risk Management, Assets, and Tags modules. None correspond to a confirmed API module today (Risk Management specifically overlaps with `TRADEOS_API_SPECIFICATION.md`'s own API-2, itself waiting on `TRADEOS_DATABASE_DESIGN.md`'s DB-3). They are not included in Section 3's table and are not designed further here — see Section 20.

---

## 4. Navigation Blueprint

### 4.1 Primary Navigation (Sidebar)
Grouped by how frequently a trader uses each module day-to-day, not strictly by Bounded Context alphabetical order:
- **Workspace:** Dashboard, Trades, Playbook, Journal
- **Analytics:** Statistics, Mistakes, Evaluation (Rule Explorer entry point)
- **Configuration:** Scoring & Catalogs
- **Reserved, visually present but inactive** (Section 18): AI Coach — shown so the information architecture doesn't need to change when it ships, not because it is usable today.

### 4.2 Secondary Navigation
Within a module, sub-views are tabs, not separate sidebar entries — e.g., within Statistics: Overview / By Dimension / Rolling (mirroring the three confirmed endpoints, `TRADEOS_API_SPECIFICATION.md` Section 6.10 exactly, one tab per endpoint, never a tab with no backing endpoint).

### 4.3 Top Bar
Page title, breadcrumb (Section 4.4), and the primary action for the current context (e.g., "+ New Trade" on the Trades module, calling `POST /trades`).

### 4.4 Breadcrumbs
`Module → Resource → Detail`, e.g., `Trades → #A1B2C3`. Always reflects the actual route (Section 2.3), never a decorative label disconnected from navigation state.

### 4.5 Quick Actions
A single global quick action, "+ New Trade," available from the Dashboard and Trades module — no other write action is frequent enough to warrant being global rather than contextual to its own page.

### 4.6 Search
**Not specified.** `TRADEOS_API_SPECIFICATION.md` Section 7.3 explicitly registered free-text search as unimplemented (Open Question API-1). The frontend must not present a search input that calls nothing — no global search bar exists in this blueprint until API-1 resolves. See Open Question FE-2 (Section 20).

### 4.7 Context Menus
A Trade row offers a contextual menu (e.g., a kebab icon) for actions that exist as confirmed endpoints only: Close, Re-evaluate, Tag Mistake, Delete (soft). No context menu item is invented for an action without a backing endpoint.

### 4.8 Keyboard Shortcuts
Reserved for **navigation only** in this blueprint (e.g., a command palette to jump between pages) — never bound to a business-mutating action (closing a trade via a keystroke, for instance), since a Domain Invariant-checked, confirmable action deserves its normal UI flow, not a shortcut that could be triggered accidentally.

### 4.9 Future Navigation Expansion
When a Future Reserved Domain (`TRADEOS_DOMAIN_MODEL.md` Section 17) ships an API module, it gains a new Primary Navigation entry (Section 4.1) — the navigation structure is additive by design, matching the API's own additive-versioning stance (`TRADEOS_API_SPECIFICATION.md` Section 12).

---

## 5. Page Blueprint

**Scoping note**, consistent with this document's own Principle 6 (Consistency Over Creativity) and the precedent set in `TRADEOS_API_SPECIFICATION.md` Section 6: the six pages most illustrative of a pattern reused elsewhere (Dashboard, Trades List, Trade Detail, Evaluation Rule Explorer, Configuration Versions, Statistics) are specified in full. The remainder are specified in compact table form, inheriting the same state/permission conventions already established.

### 5.1 Dashboard Page
- **Purpose / Business Capability:** one-screen overview, composing `GET /dashboard`.
- **Main Components:** metric cards (Win Rate, Expectancy, Profit Factor, Average R — from the composed Statistics overview), a Rolling Statistics summary card, a Mistakes ranking preview (top 3), a recent Trades list preview.
- **User Actions:** navigate into any composed section's full page; "+ New Trade."
- **Displayed Information:** exactly what `GET /dashboard` returns — no additional client-side computation (Principle 1).
- **Permissions:** authenticated user, own data only (`TRADEOS_API_SPECIFICATION.md` Section 4.6).
- **Dependencies:** Dashboard API module.
- **States:** Loading (skeleton cards), Empty (a first-time state — "Log your first trade to see your dashboard"), Error (Section 17), Success.
- **Navigation Entry:** primary, first sidebar item.
- **Future Extensibility:** a Future AI Dashboard widget (Section 9) would add one more composed card here, not restructure the page.

### 5.2 Trades List Page
- **Purpose:** browse, filter, and enter Trades.
- **Main Components:** a Table (Section 11) bound to `GET /trades`'s exact filter/sort/pagination contract; a "+ New Trade" action opening the Trade Entry form (Section 10).
- **User Actions:** filter by direction/result/date/dimension; sort; paginate; open a Trade; create a new Trade.
- **Displayed Information:** Trade summaries (per `TRADEOS_API_SPECIFICATION.md` Section 6.4's lighter list shape — no full breakdown, no checklist answers).
- **Permissions:** own Trades only.
- **Dependencies:** Trades API module.
- **States:** Loading (skeleton rows), Empty ("No trades yet"), Error, Success.
- **Navigation Entry:** primary.
- **Future Extensibility:** a future Broker Integration (Section 18) would add an "imported" indicator to a row, not change the table's shape.

### 5.3 Trade Detail Page
The flagship page, per this project's own established design history.
- **Purpose:** full detail of one Trade, its Evaluation, and everything referencing it.
- **Main Components:** a summary card (entry/exit/size/direction/computed `r_multiple` etc., from `GET /trades/{id}`); an Evaluation summary (five score visualizations, Section 12, with a link into the full Rule Explorer, Section 5.4); a Mistakes tag list with add/remove; a Journal entries list scoped to this Trade; primary actions (Amend, Close if still Open, Re-evaluate, Delete).
- **User Actions:** amend fields; close the trade; tag/untag mistakes; trigger re-evaluation; navigate to the full Evaluation history; add a trade-scoped Journal entry; delete (soft).
- **Displayed Information:** everything `GET /trades/{id}` returns, plus its nested current Evaluation summary.
- **Permissions:** own Trade only — `TRADEOS_API_SPECIFICATION.md` Section 8 confirms a non-owned Trade ID returns `404`, so this page's not-found state (Section 17) covers both "doesn't exist" and "not yours" identically, by design.
- **Dependencies:** Trades module; Evaluation module (for the summary and the link to Section 5.4); Mistakes/Catalogs (for tagging); Journal module.
- **States:** Loading, Not Found (`404` — Section 17), Error, Success; a distinct **Closing** sub-state while the Close action's request is in flight (not optimistic, Principle 8).
- **Navigation Entry:** reached only from the Trades List or Dashboard — no direct sidebar entry.
- **Future Extensibility:** an AI Coach panel (Section 18) would be an additional card on this page, reading this same Trade's data, never altering the page's existing cards.

### 5.4 Evaluation Rule Explorer Page
- **Purpose:** the full, explainable breakdown of a Trade's current (and historical) Evaluation Snapshots.
- **Main Components:** five score panels (one per Engine), each expandable into its criterion-level breakdown (`GET /trades/{id}/evaluation`); a history view listing every past snapshot (`GET /trades/{id}/evaluation/history`), each labeled with the Configuration Version that produced it.
- **User Actions:** expand a criterion's contribution detail; switch between the current snapshot and a historical one; trigger re-evaluation (also available from Section 5.3).
- **Displayed Information:** exactly the shape `TRADEOS_API_SPECIFICATION.md` Section 6.5 defines — score, grade (absent for Bias, by design), and breakdown rows (criterion, raw value, normalized value, weight, contribution).
- **Permissions:** own Trade only.
- **Dependencies:** Evaluation module.
- **States:** Loading, Empty (a Trade with no checklist answers supplied still has *a* snapshot, per Domain Invariant INV-WEIGHT-01's handling of missing inputs — so "empty" here means zero criteria contributed, a legitimate, displayable state, not an error), Error, Success.
- **Navigation Entry:** from Trade Detail only.
- **Future Extensibility:** a sixth Engine (`TRADEOS_DOMAIN_MODEL.md` Section 16) adds one more score panel, not a new page.

### 5.5 Configuration — Scoring Versions Page
- **Purpose:** manage the versioned Evaluation configuration.
- **Main Components:** a version list (status: draft/published/superseded); a version detail view showing its Criteria/Weights; a Publish action.
- **User Actions:** create a new draft (`POST /configuration/versions`); edit weights within a draft (`POST /configuration/versions/{id}/weights`); publish (`POST /configuration/versions/{id}/publish`).
- **Displayed Information:** every field `TRADEOS_API_SPECIFICATION.md` Section 6.6 defines, including the `409`/`422` business rules surfaced as inline messaging (Section 17) — e.g., attempting to edit a published version's weights is prevented in the UI *before* the request is sent (a fast-feedback client check, never the sole gate, Principle 2), and still handled correctly if the backend rejects it anyway.
- **Permissions:** own Configuration (today implicitly global to the single user, `TRADEOS_API_SPECIFICATION.md` Section 4.6).
- **Dependencies:** Configuration module.
- **States:** Loading, Empty (no versions yet — unlikely in practice since a default version should exist, but specified for completeness), Error, Success, **Publishing** (a distinct in-flight state given this action's consequence, Section 13).
- **Navigation Entry:** primary, under Configuration.
- **Future Extensibility:** a new Scoring Profile (Section 18) appears as a new column in the weights editor, not a new page.

### 5.6 Statistics Page
- **Purpose:** performance analytics, all confirmed dimensions and windows.
- **Main Components:** three tabs (Section 4.2) — Overview (`GET /statistics/overview`), By Dimension (`GET /statistics/by-dimension`, with a dimension selector matching the API's own enum: strategy/setup/session/direction), Rolling (`GET /statistics/rolling`, with the window selector: 10/20/30/50/100/200, matching the API exactly).
- **User Actions:** switch tabs; change dimension/window selectors; drill into a Playbook Setup from a by-dimension row (Section 18 cross-link).
- **Displayed Information:** exactly what each endpoint returns — no client-computed metric appears here that isn't already a named field in `TRADEOS_API_SPECIFICATION.md` Section 6.10's response shape.
- **Permissions:** own data only.
- **Dependencies:** Statistics module.
- **States:** Loading, Empty ("Not enough trade history yet" — a real, expected state given `PROJECT_AUDIT.md`'s confirmed low current trade volume), Error, Success.
- **Navigation Entry:** primary.
- **Future Extensibility:** a Pattern Discovery module (`TRADEOS_DOMAIN_MODEL.md` Section 17) would add a fourth tab, reusing this page's existing tab/filter chrome.

### 5.7 Remaining Pages (Compact)

| Page | Purpose | Key API Dependency | Notes |
|---|---|---|---|
| Login / Register | Authenticate | Authentication module | No sidebar entry; the only unauthenticated pages in the app |
| Trades — New/Edit (modal or dedicated route) | Simple/Pro trade entry (Principle 7) | `POST /trades`, `PATCH /trades/{id}` | Simple mode shows only required fields; Pro mode reveals every optional field and `checklist_answers`, per Section 10 |
| Playbook List | Browse Setups | `GET /playbook-setups` | Empty state: "No setups documented yet" |
| Playbook Setup Detail | Setup definition + live performance | `GET /playbook-setups/{id}` (which itself composes Statistics, `TRADEOS_API_SPECIFICATION.md` Section 6.8) | Performance numbers are never edited here — read-only, sourced live |
| Catalogs Management | Manage Setups/Sessions/Strategies/Entry Triggers/Mistake Tags | Catalogs module | One page, filtered by kind (mirroring the API's own `?kind=` filter, `TRADEOS_API_SPECIFICATION.md` Section 6.7) — not five separate pages |
| Mistakes Ranking | Frequency/cost/priority | `GET /mistakes/ranking` | Read-only; tagging happens from Trade Detail (Section 5.3), never from here |
| Journal List | Browse reflections | `GET /journal-entries` | Filterable by Trade or date range, matching the API exactly |
| Journal Entry Detail/Edit | Read/write one reflection | `GET/PATCH /journal-entries/{id}` | Reference type (Trade vs. period) is immutable after creation, per the API — the UI must not offer to change it |
| Settings — Profile | View/edit account email | Users module | Password change is a separate, dedicated flow (`TRADEOS_API_SPECIFICATION.md` Section 6.2) |
| Settings — Preferences | Theme, language, notifications | Preferences module | Theme selector is grounded in a real field (`TRADEOS_DATABASE_DESIGN.md` Section 6.2) — not decorative |

---

## 6. Screen Flow Blueprint

The primary user journeys between pages, each traced to the endpoints and pages already specified in Sections 4–5. No flow below introduces a step, a page, or an action not already named in this document or the API Specification.

### 6.1 Onboarding
```
Login/Register  →  Dashboard (Empty state, Section 5.1)  →  "+ New Trade" (Section 4.5)
```
A first-time user's Dashboard is legitimately empty (Section 5.1) — the flow's first meaningful action is always logging a first Trade, not browsing an empty Statistics page.

### 6.2 Log a Trade (Simple)
```
Dashboard or Trades List  →  "+ New Trade" (Section 4.5)
   →  Trade Entry, Simple mode (Section 5.7, Principle 7)
   →  Submit (POST /trades)
   →  Trade Detail (Section 5.3), showing the computed Evaluation immediately
```
Because `POST /trades` is synchronous (`TRADEOS_API_SPECIFICATION.md` Section 10), this flow has no intermediate "processing" screen — the next screen the user sees already contains the final, scored Trade.

### 6.3 Log a Trade (Pro) with Live Evaluation Preview
```
Trade Entry  →  toggle to Pro mode (Section 5.7)
   →  fill checklist_answers  →  POST /evaluation/preview fires on change (Section 5.4's underlying endpoint)
   →  score preview updates in place, non-blocking (Section 6.1 of the Forms Blueprint, Section 10)
   →  Submit (POST /trades, carrying the same checklist_answers)
   →  Trade Detail
```
The preview call and the final creation call are two distinct requests to two distinct endpoints — the preview is advisory and never itself creates or reserves anything (`TRADEOS_API_SPECIFICATION.md` Section 6.5).

### 6.4 Close an Open Trade
```
Trades List (filtered to Open, optional)  →  Trade Detail (Section 5.3)
   →  "Close" action  →  Trade Close form (Section 10)
   →  Submit (POST /trades/{id}/close)
   →  Trade Detail, now showing terminal Result and computed r_multiple/MFE/MAE fields
```

### 6.5 Explain a Score (Rule Explorer)
```
Trade Detail (Section 5.3)  →  click a Score Ring (Section 12)
   →  Evaluation Rule Explorer (Section 5.4)
   →  expand a criterion's breakdown row
   →  (optional) switch to History view  →  select a superseded snapshot  →  view its breakdown
   →  back to Trade Detail
```

### 6.6 Re-evaluate a Trade
```
Trade Detail or Rule Explorer  →  "Re-evaluate" action
   →  confirm (a Modal/Dialog, Section 7 — this action's consequence, creating a new
       permanent snapshot, warrants an explicit confirmation step even though the
       API itself requires no confirmation payload)
   →  POST /trades/{id}/reevaluate
   →  Rule Explorer now shows the new snapshot as current; the prior one remains
       reachable via History (Section 6.5) — never deleted
```

### 6.7 Tag a Mistake
```
Trade Detail (Section 5.3)  →  Mistakes section  →  "+ Add"
   →  select from Catalogs (kind=mistake_tag) via a lightweight picker
   →  POST /trades/{id}/mistakes
   →  tag appears immediately on Trade Detail; later reflected in Mistakes Ranking
       (Section 5.7) the next time that page is visited (never live-pushed, per
       Section 2.7's caching philosophy — no page auto-refreshes another open tab)
```

### 6.8 Publish a New Scoring Configuration
```
Configuration — Scoring Versions (Section 5.5)  →  "New Draft"  →  POST /configuration/versions
   →  edit weights inline (POST /configuration/versions/{id}/weights, repeatable)
   →  "Publish"  →  confirm (Modal/Dialog, given irreversibility — Section 3.5 of the API Spec)
   →  POST /configuration/versions/{id}/publish
   →  version list now shows this version Published, the prior one Superseded
   →  (no automatic re-evaluation of existing Trades — the user must separately
       visit each Trade and choose Re-evaluate, Section 6.6, exactly matching
       Domain Model Section 8.2's "never automatic" rule)
```

### 6.9 Review Performance and Drill In
```
Dashboard (Section 5.1)  →  Statistics (Section 5.6)
   →  switch to "By Dimension"  →  select a dimension (e.g., Setup)
   →  click a row  →  either:
       (a) Trades List, pre-filtered to that dimension's value, or
       (b) Playbook Setup Detail, if the dimension is Setup specifically
   →  back to Statistics
```

### 6.10 Reflect (Journal)
```
Trade Detail (Section 5.3)  →  "+ Journal Entry"  →  Journal Entry form (trade-scoped, Section 10)
   →  POST /journal-entries  →  entry appears in this Trade's Journal list

— or, independently —

Journal module  →  Journal List (Section 5.7)  →  "+ New Entry"  →  period-scoped form
   →  POST /journal-entries (with period_start/period_end, never a trade_id)
```

### 6.11 Manage Catalogs
```
Configuration  →  Catalogs Management (Section 5.7)  →  filter by kind
   →  "+ Add" (POST /catalogs) or select an entry  →  "Deactivate" (POST /catalogs/{id}/deactivate)
   →  list updates; any Trade already referencing a deactivated entry is entirely unaffected
```

---

## 7. Component Blueprint

For each: Purpose, Inputs, Outputs, Responsibilities, Reuse.

| Component | Purpose | Inputs | Outputs | Reuse Across |
|---|---|---|---|---|
| **DataTable** | Render any list endpoint's paginated result | Columns config, data rows, active filters/sort, pagination cursor | Row click, sort change, filter change, page-forward/back events | Trades, Catalogs, Journal, Configuration Criteria/Weights, Mistakes ranking (Section 11) |
| **MetricCard** | Display one named statistic with its value | Label, value, optional trend indicator | None (display-only) | Dashboard, Statistics, Playbook performance |
| **ScoreRing / ScoreBar** | Visualize one Evaluation Engine's score/grade | Score, grade (optional — absent for Bias), color intent | None | Trade Detail, Rule Explorer |
| **FilterBar** | Render the active filters for any list page | Available filter fields (per that endpoint's documented filters, `TRADEOS_API_SPECIFICATION.md` Section 7.1) | Filter-changed event | Every list page (Section 11) |
| **Form** (generic) | Render a set of fields with client-side shape/range validation (Section 10) | Field schema, current values | Submit event with validated payload | Trade Entry, Journal Entry, Configuration Criterion, Settings |
| **Modal/Dialog** | Focused, blocking interaction (confirmations, small forms) | Title, body content, primary/secondary actions | Confirm/cancel events | Delete confirmation, New Trade (Simple mode), Publish confirmation, Re-evaluate confirmation (Section 6.6) |
| **SidePanel/Drawer** | Non-blocking detail without leaving the current list | Content, open/close state | Close event | Quick-view of a Trade or Catalog entry from a list without full navigation (optional pattern — see Open Question FE-3, Section 20, on whether Trade Detail should ever be a drawer instead of a page) |
| **Tabs** | Switch between an endpoint-backed set of sub-views | Tab definitions (each bound to a real endpoint, Principle 6) | Active-tab-changed event | Statistics, Evaluation (if a future multi-view need arises) |
| **DatePicker** | Select a date or range for filtering | Current value, range mode flag | Value-changed event | Trades filtering, Journal filtering/creation |
| **SearchInput** | **Not implemented** (Section 4.6) | — | — | — |
| **Badge** | Small status/label indicator (Trade result, Grade, Catalog kind) | Label, color intent | None | Nearly every table and detail page |
| **NotificationToast** | Ephemeral confirmation or error surfacing | Message, severity | Dismiss event | Any successful write; any error (Section 17) |
| **ProgressIndicator** | In-flight action feedback (Publishing, Closing, Saving) | Active boolean, label | None | Any action-triggering button across Sections 5, 10 |
| **EmptyState** | Consistent "nothing here yet" presentation | Icon/illustration slot, message, optional primary action | Action-clicked event | Every list page (Section 2.10) |
| **SkeletonLoader** | Loading placeholder matching eventual content shape | Shape variant (row, card, detail) | None | Every page's Loading state (Section 2.9) |

---

## 8. Component Hierarchy

Illustrative component trees for the same six pages given full treatment in Section 5 — enough to guide implementation structure without prescribing exact prop names or file layout.

### 8.1 Dashboard Page
```
DashboardPage
├── TopBar (title="Dashboard", primaryAction="+ New Trade")
├── MetricCard × 4 (Win Rate, Expectancy, Profit Factor, Average R)
├── RollingSummaryCard
│   └── MetricCard × 4 (rolling variants)
├── MistakesPreviewCard
│   └── DataTable (top 3 rows, no pagination controls shown)
├── RecentTradesPreviewCard
│   └── DataTable (top N rows, no pagination controls shown; row click → TradeDetailPage)
├── EmptyState (shown instead of the above, first-time use only)
└── SkeletonLoader (shown instead of the above, Loading state)
```

### 8.2 Trades List Page
```
TradesListPage
├── TopBar (title="Trades", primaryAction="+ New Trade")
├── FilterBar (direction, result, date range, dimension fields)
├── DataTable
│   ├── Badge (per row: Direction, Result, Confidence Grade)
│   └── row click → navigates to TradeDetailPage
├── EmptyState ("No trades yet")
└── SkeletonLoader (Loading state)

NewTradeModal (opened via primaryAction)
├── Tabs (Simple / Pro — Principle 7)
├── Form (Simple: required fields only)
├── Form (Pro: full field set + checklist_answers, with an embedded live
│   ScoreRing preview bound to POST /evaluation/preview, Section 6.3)
└── ProgressIndicator (Saving state, on submit)
```

### 8.3 Trade Detail Page
```
TradeDetailPage
├── TopBar (breadcrumb: Trades → #{id}; primaryAction contextual to Trade state)
├── TradeSummaryCard (entry/exit/size/direction/r_multiple/MFE/MAE)
├── EvaluationSummaryCard
│   ├── ScoreRing × 5 (Confidence, Quality, Execution, Market Context, Bias)
│   └── "View full breakdown" link → EvaluationRuleExplorerPage (Section 8.4)
├── MistakesCard
│   ├── Badge × N (attached tags)
│   └── "+ Add" → CatalogPickerModal (kind=mistake_tag)
├── JournalEntriesCard (scoped to this trade)
│   ├── DataTable (or a simpler stacked list, given typically few entries per trade)
│   └── "+ Journal Entry" → JournalEntryForm (Modal or inline)
├── ActionBar (Amend, Close, Re-evaluate, Delete)
│   └── each action opens its own Modal/Dialog or navigates to its own form
├── NotFoundState (404 — doubles as "not yours")
└── SkeletonLoader (Loading state)
```

### 8.4 Evaluation Rule Explorer Page
```
EvaluationRuleExplorerPage
├── TopBar (breadcrumb: Trades → #{id} → Evaluation)
├── Tabs (Current / History)
├── [Current tab]
│   └── ScorePanel × 5 (one per Engine)
│       ├── ScoreRing
│       └── DataTable (breakdown rows: criterion, raw value, normalized value, weight, contribution)
├── [History tab]
│   └── DataTable (one row per past snapshot: date, configuration version, summary scores)
│       └── row click → expands into the same ScorePanel × 5 layout for that snapshot
├── "Re-evaluate" action → ConfirmModal → ProgressIndicator
└── SkeletonLoader (Loading state)
```

### 8.5 Configuration — Scoring Versions Page
```
ScoringVersionsPage
├── TopBar (title="Scoring Configuration", primaryAction="+ New Draft")
├── DataTable (versions: label, status, published date)
│   └── row click → VersionDetailPanel
├── VersionDetailPanel (SidePanel/Drawer or nested route)
│   ├── DataTable (criteria + their weights for this version)
│   ├── Form (edit a weight — disabled entirely, not just validated, if status != draft)
│   └── "Publish" action → ConfirmModal → ProgressIndicator (Publishing state)
├── EmptyState (no versions — edge case)
└── SkeletonLoader (Loading state)
```

### 8.6 Statistics Page
```
StatisticsPage
├── TopBar (title="Statistics")
├── Tabs (Overview / By Dimension / Rolling)
├── [Overview tab]
│   └── MetricCard × N (Win Rate, Expectancy, Profit Factor, Average R, Total P&L, engine averages)
├── [By Dimension tab]
│   ├── FilterBar (dimension selector: strategy/setup/session/direction)
│   ├── Chart — By-Dimension Comparison (Section 12)
│   └── DataTable (same data, tabular form)
│       └── row click → filtered TradesListPage or PlaybookSetupDetailPage
├── [Rolling tab]
│   ├── FilterBar (window selector: 10/20/30/50/100/200)
│   └── Chart — Rolling vs. Overall Comparison (Section 12)
├── EmptyState ("Not enough trade history yet")
└── SkeletonLoader (Loading state)
```

---

## 9. Dashboard Blueprint

Describing what each communicates, not its visual chart choice (Section 12 covers visualization specifics separately).

- **Overview Dashboard** (Section 5.1): "How am I doing, right now, at a glance." Composes Statistics + Rolling + Mistakes + recent Trades into the single fastest-to-scan view in the app.
- **Trading Dashboard:** realized as the Trades List page (Section 5.2) itself — there is no separate "Trading Dashboard" beyond the list/filter/detail flow already specified, since no additional confirmed capability exists to compose into one.
- **Statistics Dashboard:** the Statistics page's Overview tab (Section 5.6) — "which of my core performance numbers are strong or weak, all-time."
- **Evaluation Dashboard:** the Rule Explorer (Section 5.4) — "why did this trade score what it scored, and can I trust that."
- **Performance Dashboard:** the Statistics page's Rolling tab — "am I improving lately, compared to my own history."
- **Configuration Dashboard:** the Scoring Versions page (Section 5.5) — "what rules are currently governing my scores, and what changed."
- **Future AI Dashboard:** reserved (Section 18) — would communicate "what has the system noticed about my patterns," strictly downstream of the dashboards above, never replacing them.

---

## 10. Forms Blueprint

| Form | Purpose | API Endpoint | Validation Strategy | Error Presentation |
|---|---|---|---|---|
| Trade Entry (Simple) | Log a trade with only required facts | `POST /trades` | Client checks shape/required fields (`TRADEOS_API_SPECIFICATION.md` Section 9, layers 1–2) before submit | Inline per-field, plus a summary banner for business/invariant errors (`INVARIANT_VIOLATION`, Section 17) |
| Trade Entry (Pro) | Same, with full classification + checklist answers | `POST /trades` | Same as above, applied to the larger field set | Same |
| Trade Amendment | Correct already-recorded facts | `PATCH /trades/{id}` | Same layered validation, re-checked against the *proposed full state* exactly as the API itself does (`TRADEOS_API_SPECIFICATION.md` Section 6.4) — the frontend must not validate only the changed field | Inline, plus a visible note that this action logs a `TradeAmended` event (transparency, not a silent edit) |
| Trade Close | Transition Open → terminal Result | `POST /trades/{id}/close` | Requires `result` + `exit_price` together, mirrored client-side before submit (INV-TRADE-02) | `409` if already closed — shown as a state conflict message, not a generic error |
| Evaluation Preview | Live score feedback while filling a Checklist | `POST /evaluation/preview` | Same shape validation as checklist_answers in Trade Entry | Inline; a failed preview never blocks continuing to fill the form, since preview is advisory |
| Journal Entry | Create/edit a reflection | `POST/PATCH /journal-entries` | Enforces "exactly one of Trade or period reference" client-side before submit, mirroring the API's check constraint | A single, clear message if both or neither are supplied |
| Configuration Criterion | Define/edit a scoring criterion | `POST/PATCH /configuration/scoring-criteria` | `max_value >= min_value` checked client-side | Inline |
| Configuration Weight | Add/update a weight within a draft version | `POST /configuration/versions/{id}/weights` | `weight >= 0`; blocked entirely (not just validated) if the version isn't a draft, per Section 5.5 | A state-conflict message, not a validation error, when the version is already published |
| Settings — Profile | Update email | `PATCH /users/me` | Valid email format | `409` on duplicate email |
| Settings — Preferences | Theme/language/notifications | `PATCH /preferences` | Enum membership only | Inline |

**Autosave Strategy:** **not specified by any frozen document for any form.** Registered as **Open Question FE-4** (Section 20) rather than assumed — every form in this blueprint is submit-triggered, not autosaving, until this is explicitly decided.

**Undo Strategy:** **not specified.** A soft-deleted Trade (`DELETE /trades/{id}`) is recoverable only at the data level (`TRADEOS_DATABASE_DESIGN.md` Section 2.6), but no endpoint exposes an "undelete" action, and no frozen document describes a UI undo pattern for edits. Registered as **Open Question FE-5** (Section 20).

---

## 11. Tables Blueprint

Every table in the application is a `DataTable` (Section 7) configured per the endpoint it renders — behavior never exceeds what the bound endpoint actually supports.

| Table | Columns (representative) | Sorting | Filtering | Pagination | Selection/Bulk | Export |
|---|---|---|---|---|---|---|
| Trades | Market, Direction, Result, Entry/Exit, R-Multiple, Confidence Grade | Single field, per `TRADEOS_API_SPECIFICATION.md` Section 7.2 | Direction, Result, date range, dimension fields — exactly the API's filter set | Cursor-based (Section 7.4) | **None** — no bulk endpoint exists (`TRADEOS_API_SPECIFICATION.md` Section 15 explicitly defers batch operations) | **Not specified** — Open Question FE-6 |
| Catalogs | Kind, Name, Active | By kind, by name | `?kind=` | Cursor-based | None | Not specified |
| Configuration — Criteria | Engine, Category, Name, Range, Active | By engine | By engine type | Cursor-based | None | Not specified |
| Configuration — Weights | Criterion, Profile, Weight, Active | — | By profile | Cursor-based | None | Not specified |
| Mistakes Ranking | Tag, Frequency, Cost, Priority | By priority (default) | — | Cursor-based (though likely small enough rarely to paginate in practice) | None | Not specified |
| Journal | Date/Trade reference, Content preview | By date | By Trade ID or date range | Cursor-based | None | Not specified |

**Responsive Behavior:** below a defined breakpoint, a table's secondary columns collapse into an expandable row detail rather than horizontal scrolling — applied identically across every table in this section, per Principle 6.

**Grouping:** not offered as a distinct client-side feature anywhere — where grouping matters (e.g., "trades by strategy"), it is realized through the `by-dimension` Statistics endpoint (Section 5.6), not through client-side grouping of the raw Trades table, to avoid a second, potentially-inconsistent implementation of the same aggregation the backend already owns (Principle 1).

---

## 12. Charts Blueprint

Describing communication purpose, not a chosen charting library.

| Visualization | Purpose | Displayed Metrics | Interactions | Data Source |
|---|---|---|---|---|
| Rolling vs. Overall Comparison | "Am I trending better or worse than my own history" | Win Rate, Expectancy, Profit Factor, Average R, both windows | Change window size (10–200) | `GET /statistics/rolling` |
| By-Dimension Comparison | "Which strategy/setup/session/direction is actually working" | Win Rate, Expectancy, Profit Factor per group | Change dimension; click a group to drill into its Trades (filtered Trades List) or its Playbook Setup | `GET /statistics/by-dimension` |
| Evaluation Score Rings | "How did this trade score across all five engines, at a glance" | Confidence/Quality/Execution/Market Context (0–100 + grade), Bias (signed, no grade) | Click a ring to expand its criterion breakdown (Rule Explorer, Section 5.4) | A Trade's nested `evaluation` object |
| Mistakes Frequency/Cost | "Which mistake actually costs me the most, not just happens the most" | Frequency, total cost, priority, per tag | Sort by frequency vs. cost vs. priority | `GET /mistakes/ranking` |

**Timeframe Selection:** only where the underlying endpoint supports it (Rolling's window parameter, Trades' date filters) — no chart offers a timeframe control disconnected from an actual query parameter.

**Comparison Capability:** explicitly limited to what's named above (Rolling vs. Overall, cross-dimension) — no generic "compare any two things" builder is specified, since none is a confirmed capability.

**Drill-Down:** always navigates to an existing page (Trades List filtered, Playbook Setup Detail) — never opens a chart-specific mini-view with its own separate data-fetching logic.

**Export Capability:** **not specified anywhere in the six frozen documents** (the Reports module remains unconfirmed, `TRADEOS_API_SPECIFICATION.md` Section 18, API-6). No chart in this blueprint offers an export action. Open Question FE-6 (Section 20) covers this uniformly for both tables and charts.

**Equity Curve:** notably, **no confirmed endpoint returns a ready-to-plot equity curve** (a running cumulative P&L series). Computing one client-side from a fetched Trades list would be exactly the kind of frontend-side business computation Principle 1 and Principle 2 forbid — even though it is visually tempting and existed in the prior prototype. This is registered as **Open Question FE-7** (Section 20) rather than silently implemented by summing P&L in a component.

---

## 13. UI State Management

| State | Meaning | Example |
|---|---|---|
| **Loading** | Initial fetch in flight, no prior data to show | First visit to Trades List |
| **Refreshing** | Re-fetching where stale data is still visibly shown | Returning to Dashboard after navigating away and back |
| **Saving** | A write request in flight | Submitting Trade Entry |
| **Error** | The most recent operation failed (Section 17) | A `500` on `GET /statistics/overview` |
| **Validation** | Client-side shape/range check failed before submission | Missing required Trade field |
| **Read-only** | Data displayed but not editable in this context | Playbook performance figures (Section 5, always sourced live, never edited) |
| **Draft** | Unsaved, in-progress form content | A partially-filled Trade Entry form — **not** persisted anywhere unless Open Question FE-4 (autosave) is resolved |
| **Offline** | No connectivity detected | See Section 2.11 — minimally handled, not designed as a full mode |
| **Synchronization** | **Not applicable** — there is no client-side data store requiring reconciliation with the server, since Section 2.7's caching stance treats server state as always-refetch-on-need, not a local store to keep in sync |

---

## 14. Design System Blueprint

Consistency principles, not chosen values (no colors, no CSS, per this document's own mandate).

- **Spacing:** one consistent scale, applied identically across every component in Section 7 — a component that invents its own spacing unit is a defect.
- **Typography:** a small, fixed set of text styles (heading levels, body, label, monospace-for-numeric-data — Trade prices and R-multiples benefit from tabular/monospace figures for scannability) — not a free choice per page.
- **Icons:** one icon set, used consistently for the same concept everywhere (e.g., the same "close" icon for Trade closure and dialog dismissal only if they are conceptually the same action — otherwise distinct icons, never the same icon overloaded for two different meanings).
- **Cards, Buttons, Inputs, Dialogs, Tables:** each is exactly the component defined in Section 7 — the Design System is not a separate concern from the Component Blueprint, it is that blueprint's visual consistency layer.
- **Charts:** consistent color-to-meaning mapping across every visualization in Section 12 (e.g., whatever color means "profit" means profit everywhere, never something else in one chart and profit in another).
- **Animations:** used only to communicate a state change already defined in Section 13 (a save completing, a panel opening) — never decorative motion with no state meaning.
- **Elevation:** a small, fixed set of levels (base, raised card, modal/dialog) — not a continuous, page-specific choice.
- **Dark Theme:** the default, and the only theme designed in detail here.
- **Future Theme Support:** directly grounded, not speculative — `preferences.theme` is already a real, confirmed field (`TRADEOS_DATABASE_DESIGN.md` Section 6.2). A light theme is an additive set of values applied to the same component definitions in Section 7, never a parallel component library.

---

## 15. Accessibility

- **Keyboard Navigation:** every interactive element in Section 7 (table rows, form fields, tabs, dialogs) is reachable and operable via keyboard alone, including the navigation shortcuts in Section 4.8.
- **Focus Management:** opening a Modal/Dialog (Section 7) traps and returns focus correctly; closing one returns focus to the element that opened it.
- **ARIA:** every component in Section 7 declares appropriate roles/labels as part of its specification, not bolted on afterward — a DataTable communicates its sort state, a ProgressIndicator its busy state, etc.
- **Screen Readers:** dynamic state changes (Section 13) that aren't purely visual (an error appearing, a save completing) are announced, not only shown.
- **Contrast Requirements:** the Design System's color choices (deferred, Section 14) must meet a standard contrast ratio — a requirement stated here even though the values themselves are out of this document's scope.
- **Responsive Behavior:** covered in Section 11 (tables) and applies identically to every other component — accessibility and responsiveness are treated as one continuous requirement, not two separate passes.
- **Philosophy:** accessibility is a property of each component's *definition* (Section 7), never a separate audit performed after the fact — this is Principle 4 (Section 1) restated as an implementation discipline.

---

## 16. Performance

- **Lazy Loading / Code Splitting:** per feature module (Section 2.4) — a user who only ever uses Trades and Statistics never downloads the Configuration module's code until they navigate there.
- **Virtualized Tables:** required for the Trades table specifically, given the confirmed 20,000+ trade scalability target (`TRADEOS_PRODUCT_BIBLE.md` Non-Functional Requirement 10.2) — rendering every row in the DOM at that volume is not viable. Other tables (Catalogs, Configuration Criteria/Weights) are small enough today that virtualization is not required, consistent with avoiding premature optimization.
- **Caching:** per Section 2.7 — short-TTL for Configuration/Catalogs, always-fresh for Trades/Statistics/Evaluation.
- **Prefetching:** limited to genuinely predictable next-navigation (e.g., prefetching a Trade's detail data on hover over its row in the Trades List) — not a blanket prefetch-everything strategy.
- **Image Optimization:** applies to Playbook Setup attachments (`TRADEOS_DATABASE_DESIGN.md` Section 6.16's `file_reference`) — the only place the application handles user-supplied images today.
- **Bundle Organization:** mirrors feature organization (Section 2.4) exactly — one bundle boundary per feature module, not a single monolithic bundle nor an arbitrary split unrelated to the application's own structure.
- **Performance Philosophy:** the core loop (logging a Trade, viewing today's Dashboard) must feel instantaneous (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.1) — every performance decision above exists to protect that specific experience first, analytical/configuration screens second, exactly matching the priority order `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9 already established for the system as a whole.

---

## 17. Error Experience

| Error Category (API code) | Presentation | Recovery |
|---|---|---|
| `VALIDATION_FAILED` | Inline, per-field, at the point of input | User corrects and resubmits — no page reload |
| `INVARIANT_VIOLATION` | A clear, plain-language message naming what business rule was violated (not just the raw `INV-TRADE-01`-style code) — the code is preserved in the background for support/debugging (`trace_id`, `TRADEOS_API_SPECIFICATION.md` Section 8) but never shown to the user as their primary message | User adjusts the conflicting fields |
| `UNAUTHENTICATED` (`401`) | Redirect to Login, preserving the attempted destination for post-login return | Re-authenticate |
| `FORBIDDEN` (`403`) / `NOT_FOUND` (`404`) | A single "not found" presentation for both, on Trades/Journal specifically (mirroring the API's own deliberate non-disclosure, `TRADEOS_API_SPECIFICATION.md` Section 8) | Navigate back |
| `CONFLICT` (`409`) | A state-conflict message specific to the action (e.g., "This trade is already closed") | Refresh the resource's current state |
| `RATE_LIMITED` (`429`) | A clear "slow down" message, distinct from a generic error | Automatic retry after the indicated delay, where the API supplies one |
| `INTERNAL_ERROR` (`500`) | A generic, reassuring message plus the `trace_id` visibly available (for support), never raw internal detail | Retry action offered; if retried via a `POST`, the same `Idempotency-Key` is reused (`TRADEOS_API_SPECIFICATION.md` Section 3.6) so a retry never double-creates |
| Network error (no response at all) | Distinct from `INTERNAL_ERROR` — "couldn't reach the server," pairs with the Offline state (Section 2.11) | Retry |

**User Messaging Philosophy:** the user is always told what happened and, wherever possible, what to do next — never shown a raw error code as the primary message, and never told something succeeded when the API's response says otherwise (no optimistic success messaging ahead of the actual response, Principle 8).

---

## 18. Future Extensibility

Because Sections 2–3 organize the frontend by feature, one-to-one with confirmed Bounded Contexts and API modules, every Future Reserved Domain (`TRADEOS_DOMAIN_MODEL.md` Section 17) is additive:

- **AI Coach:** a new feature module and a new Primary Navigation entry (Section 4.1, already visually reserved); consumes existing pages' data (Trade Detail, Statistics) without altering them, mirroring its backend design as a downstream-only consumer (`TRADEOS_API_SPECIFICATION.md` Section 17).
- **Broker Integrations:** adds an "imported" indicator and a sync-status affordance to the existing Trades List/Detail — never a new Trade data model or a parallel trades view.
- **Plugin Marketplace:** would require its own new feature module and, per `TRADEOS_API_SPECIFICATION.md` Section 17, its own service-to-service auth model — entirely out of this blueprint's current scope, reserved only.
- **Multi-User / Teams / Workspaces:** conditional on Product Bible Open Question 2. If it resolves toward yes, the frontend's ownership-scoping assumption (every page already scoped to "my data," Section 5) extends to "my workspace's data" — an additive scoping change to existing pages' data-fetching, not a new set of pages.
- **Mobile:** the responsive requirement (Principle 5, Section 1) already targets this — a dedicated native app, if ever built, would consume the same API (`TRADEOS_API_SPECIFICATION.md` Section 17) and could reuse this blueprint's Page/Component definitions as its own specification starting point, not require a separate blueprint from scratch.

---

## 19. Traceability Matrix

| Business Capability | Frontend Module | Page | Key Components | API Module | Database Module |
|---|---|---|---|---|---|
| Register and score a trade | Trading | Trade Entry, Trade Detail | Form, ScoreRing, MetricCard | Trades, Evaluation | `trading` |
| Explain a historical score | Evaluation | Rule Explorer | ScoreRing, DataTable (breakdown) | Evaluation | `trading.evaluation_snapshot_breakdowns` |
| Preview a score before saving | Evaluation | Trade Entry (embedded) | ScoreRing (live) | Evaluation | *(no table)* |
| Manage scoring configuration | Configuration | Scoring Versions | DataTable, Form | Configuration | `configuration` |
| Manage reference lists | Configuration | Catalogs Management | DataTable, Form | Catalogs | `configuration.catalog_entries` |
| Document and track a setup | Playbook | Playbook List, Playbook Setup Detail | DataTable, MetricCard | Playbook | `playbook` |
| Understand recurring errors | Mistakes | Mistakes Ranking | DataTable, chart (Section 12) | Mistakes | *(no table)* |
| Understand performance | Statistics | Statistics (3 tabs) | MetricCard, charts, Tabs | Statistics | *(no table)* |
| Reflect qualitatively | Journal | Journal List, Journal Entry Detail | DataTable, Form | Journal | `journal` |
| Authenticate | Authentication | Login, Register | Form | Authentication | `identity` |
| Personalize the app | Settings | Settings — Preferences | Form | Preferences | `preferences` |
| One-screen overview | Dashboard | Dashboard | MetricCard, DataTable preview | Dashboard (composition) | *(composition of the above)* |

Every page in Section 5 appears in, or is a variant of, a row above — matching the same standard `TRADEOS_API_SPECIFICATION.md` Section 19 and `TRADEOS_DOMAIN_MODEL.md` Section 18 already established for their own layers.

---

## 20. Known Gaps

| ID | Topic | Current State | Reason | Priority |
|---|---|---|---|---|
| FE-1 | Offline behavior | Not designed — minimal "you're offline" state only (Section 2.11) | No frozen document specifies an offline/sync strategy for a stateless, always-connected API | Low |
| FE-2 | Global search | Not implemented — no search UI exists | Depends on `TRADEOS_API_SPECIFICATION.md` API-1 (free-text search) resolving first | Low, rising if API-1 is prioritized |
| FE-3 | Trade Detail as page vs. drawer | Specified as a full page (Section 5.3) | A drawer/side-panel alternative is plausible but not required by any frozen document; the fuller Rule Explorer/Journal content favors a page | Low |
| FE-4 | Autosave strategy | Not specified for any form | No frozen document describes autosave behavior for Trade Entry, Journal, or Configuration forms | Medium — affects real day-to-day data-entry risk (losing a half-filled Trade Entry) |
| FE-5 | Undo strategy | Not specified beyond soft-delete's data-level recoverability | No frozen document describes a UI-level undo pattern | Low |
| FE-6 | Export capability (tables and charts) | Not implemented anywhere | The Reports module is unconfirmed (`TRADEOS_API_SPECIFICATION.md` API-6) | Low |
| FE-7 | Equity curve visualization | Not implemented — no confirmed endpoint supplies this data shape | Computing it client-side from raw Trades would violate Principle 1/2 (Single Source of Truth, Smart Backend); needs either a new Statistics endpoint or an explicit decision that the frontend may aggregate already-fetched, already-correct per-trade P&L values for *display only* — **the user has confirmed (see Document Control) that this must be produced by the backend**, so the resolution direction is set even though the endpoint itself does not yet exist | Medium — a real, likely-wanted visualization, direction confirmed, endpoint still to be specified |
| FE-8 | "Trading Accounts," "Calendar," "Reports," "AI," "Notifications" modules | No confirmed API module (see `TRADEOS_API_SPECIFICATION.md` API-4, API-5, API-6) | Carried forward, not re-litigated independently | Low |
| FE-9 | Prior prototype modules (Watchlist, Risk Management, Assets, Tags) | Not carried into this blueprint | No corresponding Bounded Context, API module, or database module exists for any of them | Low — would require upstream architecture work first, not a frontend decision |

---

## 21. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial Frontend Blueprint. Derived from all six frozen foundational documents. Defined frontend principles, architecture, application structure (mirroring confirmed API modules 1:1), navigation, a full page blueprint (six pages in full detail, the remainder compact), a reusable component blueprint, dashboard/forms/tables/charts blueprints, UI state model, design system principles (no colors/CSS), accessibility, performance, error experience, future extensibility, a full traceability matrix, and nine registered Open Questions (FE-1 through FE-9) rather than invented answers. Explicitly reconciled against the prior `TradeOS_UI_v3` prototype, carrying forward only what the six frozen documents actually confirm. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Added Screen Flow Blueprint (Section 6, eleven primary user journeys, each traced to already-specified pages and endpoints) and Component Hierarchy (Section 8, illustrative component trees for the six fully-specified pages). Confirmed, per explicit approval, that the Equity Curve (Open Question FE-7) must be produced by the backend to preserve Single Source of Truth — the frontend will not compute it client-side once an endpoint exists. Renumbered all sections accordingly; corrected two internal cross-references that had drifted to a stale section number during drafting. |

**Status:** FROZEN. This is the seventh permanent foundational document of TradeOS, after `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`, and `TRADEOS_API_SPECIFICATION.md`.
**Next document:** to be determined.
