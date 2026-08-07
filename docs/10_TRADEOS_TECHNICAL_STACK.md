# 10_TRADEOS_TECHNICAL_STACK.md

**Document Status:** CANONICAL AND FROZEN — the official technical stack and engineering standard of TradeOS.
**Version:** 1.1
**Last Updated:** 2026-08-07
**Depends On:** all nine prior frozen documents — `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md` v2.1, `TRADEOS_DOMAIN_MODEL.md` v1.1, `TRADEOS_SYSTEM_ARCHITECTURE.md` v1.2, `TRADEOS_DATABASE_DESIGN.md` v1.1, `TRADEOS_API_SPECIFICATION.md` v1.1, `TRADEOS_FRONTEND_BLUEPRINT.md` v1.1, `TRADEOS_BACKEND_BLUEPRINT.md` v1.1, `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` v1.0 (all frozen).
**Redesigns:** nothing. Every technology named here either (a) restates a decision already frozen upstream — FastAPI, Python, PostgreSQL, React + TypeScript, REST/JSON, JWT auth, pytest — with no change, or (b) fills a genuine gap those documents left at the "class of tool" level (e.g., "a database migration tool" without naming one) with exactly one official choice and a citable rationale. Where a choice would require reopening an already-frozen decision, it is registered as an Open Question (Section 20) instead.
**Is Not:** an architecture document, a redesign of the Domain Model/Database Design/API Specification/Frontend or Backend Blueprints, or a restatement of the Implementation Master Plan's phases and sequencing. This document answers *which tools and conventions*, never *what the system is* or *in what order it is built*.
**Audience:** every future contributor, human or Claude Code, writing production code for TradeOS. This is the engineering standard that governs *how* code is written, not *what* it does.

---

## 1. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-25 | Initial Technical Stack. Restated every technology decision already frozen upstream (FastAPI, Python, PostgreSQL, React + TypeScript, REST/JSON, JWT, pytest, Alembic) without alteration, and made exactly one official selection — with rationale, alternatives considered, and explicit rejections — for every tooling category the prior nine documents left open at the "class of tool" level (build tool, ORM, state management, styling, testing tools, linters, CI/CD, security tooling). Registered four genuine, previously-unaddressed Open Questions (Section 20) rather than inventing answers for them. |
| 1.1 | 2026-08-07 | Sprint 9.4 (Deployment Readiness & Operational Hardening). Section 20: resolved OQ-8 — GitHub is confirmed as the code-hosting platform (`git remote -v`, `CHANGELOG.md`). Section 12: recorded that the CI pipeline (linting, type-checking, unit/integration tests, build) is now implemented via three separate GitHub Actions workflows, covering a documented subset of this section's own described pipeline (no Playwright E2E stage, no staging auto-deploy, no production approval gate — all remain future work). Section 14: recorded that Dependabot and the `pip-audit`/`pnpm audit`/Trivy vulnerability scanners, previously chosen but unimplemented, are now wired into that same CI. Neither change alters any technology selection already made in this document — both are implementation-status notes on decisions already frozen. |

**Status:** FROZEN. This is the tenth document of TradeOS, after `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`, `TRADEOS_API_SPECIFICATION.md`, `TRADEOS_FRONTEND_BLUEPRINT.md`, `TRADEOS_BACKEND_BLUEPRINT.md`, and `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`.
**Next document:** to be determined — candidates named in Section 20 should be resolved before Phase 9 (Deployment) of the Implementation Master Plan is entered.

---

## 2. Purpose

The nine prior documents establish *what* TradeOS is, *how* it is architected, and *in what order* it is built. None of them is a governance document for the day-to-day engineering decisions every contributor makes dozens of times per week — which formatter, which test runner, which state management approach, which CI provider. Left unanswered, each of those questions would otherwise be re-decided ad hoc, by whichever contributor (or Claude Code session) happens to be writing code that day, producing exactly the kind of silent, uncoordinated drift `PROJECT_AUDIT.md` found repeatedly in the Excel's own history — just at the tooling level instead of the business-logic level.

This document exists to give every future contributor one answer, cited to a rationale, for every recurring technical choice — so that "which testing library do we use" has the same standing, non-negotiable answer in month one and month twelve of implementation.

---

## 3. Scope

This document defines, for the entire TradeOS codebase:

- The official production technology stack for frontend, backend, and database (Sections 6–8).
- The development environment every contributor and CI pipeline must reproduce (Section 9).
- The testing stack across every test level the Backend and Frontend Blueprints already require (Section 10).
- Code quality tooling — formatters, linters, type checkers, commit and branching conventions (Section 11).
- CI/CD pipeline shape (Section 12) and deployment target classes (Section 13).
- Security tooling at the engineering-standard level (Section 14).
- Performance engineering guidelines that operationalize, but do not redesign, already-frozen Non-Functional Requirements (Section 15).
- Explicitly rejected technologies and why (Section 16).
- A versioning and dependency-review policy (Section 17).
- A concrete, checkable Implementation Readiness Checklist (Section 18) and full traceability back to the nine canonical documents (Section 19).

---

## 4. Out of Scope

This document does not, and per its own mandate must not:

- Alter any business rule, domain concept, Bounded Context, database table, API endpoint, frontend page, backend module, or implementation phase/sprint already frozen in the nine prior documents.
- Choose a specific cloud provider. `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1 commits only to a *class* of managed hosting platform ("a Railway/Fly.io/Render-equivalent") and this document preserves that same class-level commitment (Section 13) rather than narrowing it to one named vendor, since no upstream document requires a specific one.
- Resolve any Product Bible Open Foundational Question, any Domain Model/Database Design/API Specification/Frontend/Backend Blueprint open item, or any Implementation Master Plan blocking Open Question (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Section 16). Where a tooling decision is genuinely contingent on one of those, it is named here as an Open Question (Section 20), never silently assumed.
- Plan implementation order, sprints, or milestones — that is `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`'s exclusive concern. This document is orthogonal to that one: the Master Plan says *when*, this document says *with what*.
- Introduce a caching layer, background job system, or asynchronous message bus. All three remain explicitly deferred upstream (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04, ADR-05; `TRADEOS_BACKEND_BLUEPRINT.md` Section 10) until a real, demonstrated need exists — this document does not pre-select a technology for a capability that isn't being built yet.

---

## 5. Technology Selection Principles

These govern every selection in Sections 6–17. They are the tooling-level counterpart to `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 1's Architectural Principles — narrower, and directly enforceable when evaluating a new dependency.

1. **Domain First.** No tool may require restructuring the Domain layer to accommodate it (`TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 7, restated at the tooling level). A library that only fits if `EvaluationEngine` stops being a pure, dependency-free function is rejected regardless of its other merits.
2. **Simplicity Over Novelty.** A tool is chosen for what it solves today, never for what it might enable speculatively (`TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 4). This is why, for example, this document selects no caching technology at all (Section 7) rather than pre-installing one "just in case."
3. **Long-Term Maintainability.** TradeOS is maintained, today, by one person (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2). Every tool is evaluated on whether it can still be understood and safely changed a year from now with no institutional memory beyond this document — this is `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9's Maintainability ranking (#3, above Security and Performance) applied to tool selection specifically.
4. **Strong Typing.** Every layer that can be typed, is — Python type hints checked by a static type checker (Section 11), TypeScript in strict mode, Pydantic models mirroring API contracts. This directly extends the rationale `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8 already gave for choosing React + TypeScript in the first place: "typed contracts... reduce an entire class of integration bugs."
5. **Mature Ecosystems.** A tool with multi-year adoption, an active maintenance history, and broad community troubleshooting is preferred over a newer alternative with theoretically superior design but a thinner track record — directly serving Reliability (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9, priority #2).
6. **Excellent Documentation.** A tool a solo maintainer cannot self-serve troubleshoot from its own documentation is a Maintainability risk regardless of its capability.
7. **Low Vendor Lock-In.** Preference for open standards and portable formats (SQL over a proprietary query DSL, OpenAPI-compatible REST over a vendor-specific protocol) — consistent with `TRADEOS_PRODUCT_BIBLE.md` Principle 1 (The Trader Owns Their Data) extended to the codebase's own portability.
8. **Incremental Evolution.** A tool must be adoptable and replaceable module-by-module, never requiring a big-bang migration — the same reversibility standard `TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 6 already applies to architectural decisions, applied here to tooling.

---

## 6. Frontend Stack

**Framework standing decision:** React + TypeScript is already frozen and unchanged (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8, corrected in v1.2 Section 8.5 to clarify this was never contingent on the `TradeOS_UI_v3` prototype). Every choice below is made *within* that already-approved framework, never around it.

| Category | Official Choice | Status |
|---|---|---|
| Framework | **React 18+** | MANDATORY (frozen, `TRADEOS_SYSTEM_ARCHITECTURE.md` §8) |
| Language | **TypeScript, strict mode** | MANDATORY (frozen, same section) |
| Build Tool | **Vite** | MANDATORY (this document) |
| Routing | **React Router** | MANDATORY (this document) |
| State Management (UI state) | **React `useState`/`useContext`, component/feature-local** | MANDATORY (this document) |
| State Management (server state) | **TanStack Query** | MANDATORY (this document) |
| Forms | **React Hook Form** | MANDATORY (this document) |
| Validation | **Zod** | MANDATORY (this document) |
| UI Components | **Radix UI Primitives** (headless) | MANDATORY (this document) |
| Styling | **Tailwind CSS** | MANDATORY (this document) |
| Icons | **lucide-react** | MANDATORY (this document) |
| Charts | **Recharts** | MANDATORY (this document) |
| Tables | **TanStack Table + TanStack Virtual** | MANDATORY (this document) |
| Date Handling | **date-fns** (+ `date-fns-tz` where timezone conversion is needed) | MANDATORY (this document) |
| Notifications (UI toast) | **Sonner** | RECOMMENDED (this document) |
| File Uploads | **Native `File`/`FormData` APIs, no third-party library** | RECOMMENDED (this document) |
| Theme Management | **React Context + Tailwind `class`-based dark mode** | MANDATORY (this document) |

### 6.1 Build Tool — Vite
**Why selected:** `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1 requires "static hosting for the React/TypeScript build, served independently of the backend" — a pure client-side single-page application, not a server-rendered one. Vite produces exactly that: a static asset bundle with no Node server required at runtime. Its dev server's near-instant hot module replacement also directly serves `TRADEOS_PRODUCT_BIBLE.md` NFR 10.1 (the core loop must feel instantaneous) at development time, not only in production.
**Why it fits TradeOS specifically:** `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.4 requires feature-based code splitting/lazy loading (Section 16 there) — Vite's Rollup-based production build handles this natively with zero extra configuration.
**Alternatives considered:** **Next.js** — rejected (Section 16): its default model assumes server-side rendering and API routes running on a Node server, which directly contradicts `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.1's "no server-rendered business logic, and no secondary backend" and `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1's static-hosting decision. Adopting Next.js would require either running it in a mode that fights its own design (static export, forgoing most of its value) or introducing a second backend surface nothing upstream calls for. **Create React App** — rejected as unmaintained/deprecated by its own ecosystem; no longer a mature-ecosystem choice per Section 5, Principle 5.

### 6.2 Routing — React Router
**Why selected:** the de facto standard client-side router for React SPAs; directly supports `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.3's "one route per Page, with nested routes for sub-resources exactly mirroring the API's own resource nesting."
**Alternatives considered:** TanStack Router — a newer, fully type-safe alternative; not chosen because React Router's longer adoption history and documentation depth outweigh the marginal type-safety gain for a single-maintainer project (Section 5, Principles 3, 5, 6).

### 6.3 State Management
**Why this split:** `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.5 already draws the exact boundary this document implements — Server State (from the API, possibly stale) versus UI State (no backend meaning). No single library covers both well, so this document deliberately does not force one.
- **Server state — TanStack Query.** Its per-query `staleTime`/`cacheTime` controls map directly onto `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.7's Caching Philosophy: a short TTL for Configuration/Catalog reads, always-refetch-on-navigation for Trades/Statistics/Evaluation. This is not a generic recommendation — it is the one library whose core feature set was designed for exactly the caching split the Frontend Blueprint already specifies.
- **UI state — plain React state/Context, no library.** `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.5 explicitly scopes UI state as "local to the component or feature" — this is already a solved problem with React's built-in primitives, and introducing Redux, Zustand, or any global store would be unjustified complexity per Section 5, Principle 2 (Simplicity Over Novelty). Redux and Zustand are explicitly not selected (Section 16).

### 6.4 Forms & Validation — React Hook Form + Zod
**Why selected:** `TRADEOS_FRONTEND_BLUEPRINT.md` Principle 7 (Progressive Disclosure) requires Trade Entry to support a "Simple" path (required fields only) and a "Pro" path (every optional field the API accepts) without becoming two separate forms — React Hook Form's schema-driven, uncontrolled-input model handles this precisely, with materially better performance at large, mostly-optional forms than controlled-input alternatives. Zod schemas can mirror `TRADEOS_API_SPECIFICATION.md` Section 6.4's request body shapes directly in TypeScript, and the same schema doubles as the request payload's compile-time type — directly serving Section 5 Principle 4 (Strong Typing).
**Alternatives considered:** Formik — rejected as materially slower on large forms and less actively evolved than React Hook Form as of this document; Yup — rejected in favor of Zod for better native TypeScript inference (no separate `@types` package needed).

### 6.5 UI Components — Radix UI Primitives
**Why selected:** `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14 (Design System) deliberately specifies *consistency principles*, not chosen visual values — "no colors, no CSS." That means TradeOS needs accessible component *behavior* (focus trapping in a Dialog, correct ARIA roles on a Tabs component, keyboard navigation in a Dropdown) without a pre-baked visual opinion. Radix supplies exactly that: unstyled, fully accessible primitives, which is precisely what `TRADEOS_FRONTEND_BLUEPRINT.md` Section 15 (Accessibility) requires "as part of [a component's] definition, not bolted on afterward."
**Why it fits TradeOS specifically:** every accessibility requirement named in Section 15 there (focus management, ARIA roles, keyboard navigation) is something Radix already solves correctly, rather than something this project would need to re-implement per component.
**Alternatives considered:** a fully pre-styled component library (e.g., Material UI, Ant Design) — rejected because their opinionated visual design would fight, not serve, `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14's own custom Design System (spacing scale, typography, dark-theme-first); building every accessible primitive from scratch — rejected as reinventing already-solved, hard-to-get-right behavior (focus trapping, roving tabindex) for no benefit.

### 6.6 Styling — Tailwind CSS
**Why selected:** enforces exactly the "one consistent spacing scale," "small, fixed set of text styles," and "small, fixed set of elevation levels" `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14 requires, as configuration rather than convention — a developer cannot easily invent an off-scale spacing value the way they could in freeform CSS. Utility classes compile away unused styles, directly serving `TRADEOS_FRONTEND_BLUEPRINT.md` Section 16's bundle-size performance guidance.
**Alternatives considered:** CSS Modules — rejected as providing no built-in mechanism to *enforce* a shared scale (Section 14's core requirement), only a convention a contributor could still bypass; styled-components/Emotion (CSS-in-JS) — rejected (Section 16) for their runtime style-injection cost, which cuts against `TRADEOS_FRONTEND_BLUEPRINT.md` Section 16's performance guidance, and for weaker synergy with Radix's headless, class-driven styling model than Tailwind's.

### 6.7 Icons — lucide-react
**Why selected:** a single, consistent, tree-shakeable icon set, directly satisfying `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14's "one icon set, used consistently for the same concept everywhere." Pairs naturally with the Radix + Tailwind foundation already selected (Sections 6.5–6.6), which share the same ecosystem convention.
**Alternatives considered:** Font Awesome — rejected as heavier and less tree-shakeable; Material Icons — rejected as visually tied to Material Design, which would fight the custom Design System (Section 6.5's rationale applies equally here).

### 6.8 Charts — Recharts
**Why selected:** a declarative, React-idiomatic charting library well suited to Statistics (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 12) and the eventual Equity Curve (Open Question FE-7, deferred pending a backend endpoint per `TRADEOS_FRONTEND_BLUEPRINT.md` Section 20) — its component-based API maps directly onto `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14's "consistent color-to-meaning mapping across every visualization" requirement, since colors are passed as ordinary component props, not buried in a separate charting DSL.
**Alternatives considered:** Chart.js — rejected as canvas-based and less naturally composable with React's component model; D3 directly — rejected as far lower-level than this project needs, requiring bespoke work Recharts already provides out of the box (Section 5, Principle 2).

### 6.9 Tables — TanStack Table + TanStack Virtual
**Why selected:** `TRADEOS_FRONTEND_BLUEPRINT.md` Section 16 explicitly requires virtualization for the Trades table at the confirmed 20,000+ trade scale (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.2). TanStack Table is headless (fitting the same Radix/Tailwind foundation, Section 6.5) and pairs with TanStack Virtual for row virtualization without adopting a second, differently-styled table component for the one table that needs it.
**Alternatives considered:** AG Grid — rejected as a heavier, more opinionated (and commercially licensed for advanced features) solution than TradeOS's confirmed scale requires; a hand-rolled virtualized table — rejected as unnecessary reinvention (Section 5, Principle 2).

### 6.10 Date Handling — date-fns
**Why selected:** lightweight, tree-shakeable, works with native immutable `Date` semantics rather than a mutable wrapper. Needed because `TRADEOS_DATABASE_DESIGN.md` Section 2.5 stores every timestamp as `TIMESTAMPTZ` in UTC and explicitly defers local-time display to "a `preferences` concern" — date-fns (plus `date-fns-tz` for the actual UTC→local conversion) is the mechanism that concern is implemented with, once Open Question OQ-7 (Section 20) — where the display timezone itself comes from — is resolved.
**Alternatives considered:** Moment.js — rejected (Section 16) as a legacy library in maintenance mode by its own authors' recommendation, with a mutable-date API that invites exactly the kind of subtle bug class `PROJECT_AUDIT.md` found repeatedly elsewhere in this project's history; Luxon/Day.js — both viable, but date-fns's function-per-operation, fully tree-shakeable design is preferred for bundle size (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 16).

### 6.11 Notifications (UI Toast) — Sonner
**Note on terminology:** this is a **transient UI feedback mechanism** (e.g., "Trade saved") — it is unrelated to, and must never be confused with, the reserved **Notifications** Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 17), which is a business-domain concept (alerting a trader about a Checklist incompletion, etc.) with no implementation scheduled in `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`.
**Why selected:** built-in ARIA live-region announcement support, directly serving `TRADEOS_FRONTEND_BLUEPRINT.md` Section 15's requirement that "dynamic state changes that aren't purely visual... are announced, not only shown."
**Alternatives considered:** react-hot-toast — a close, viable alternative; Sonner is preferred for slightly more complete accessibility defaults out of the box, marginally reducing custom work needed to satisfy Section 15.

### 6.12 File Uploads — Native Browser APIs
**Why selected:** the only file-upload surface in the entire frozen scope is Playbook Setup attachments (`TRADEOS_DATABASE_DESIGN.md` Section 6.16), a low-frequency, low-complexity upload path. The native `File`/`FormData` APIs, wrapped in one small custom component per `TRADEOS_FRONTEND_BLUEPRINT.md` Section 7's reusable-component philosophy, are fully sufficient — introducing a third-party upload library (progress bars, resumable uploads, drag-and-drop) for this one, infrequent use case would be disproportionate (Section 5, Principle 2). **Note:** the actual object storage backend those files are uploaded *to* is not chosen by this document — see Open Question OQ-6 (Section 20).

### 6.13 Theme Management — React Context + Tailwind Dark Mode
**Why selected:** `TRADEOS_DATABASE_DESIGN.md` Section 6.2 already confirms `preferences.theme` as a real, persisted field, and `TRADEOS_FRONTEND_BLUEPRINT.md` Section 14 confirms dark theme is "the default, and the only theme designed in detail" today, with light theme as an additive future set of values. A single React Context reading `preferences.theme` and toggling Tailwind's `class`-based dark mode strategy is the minimal mechanism that satisfies both facts without inventing anything not already frozen.

---

## 7. Backend Stack

**Framework standing decision:** Python + FastAPI is already frozen and unchanged (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8: "already the reference implementation's choice; async-capable"). Every choice below is made *within* that already-approved framework.

| Category | Official Choice | Status |
|---|---|---|
| Framework | **FastAPI** | MANDATORY (frozen, `TRADEOS_SYSTEM_ARCHITECTURE.md` §8) |
| Language | **Python 3.12+** | MANDATORY (frozen framework; version per this document) |
| ORM | **SQLAlchemy 2.0 (async, `asyncpg` driver)** | MANDATORY (this document; consistent with the reference implementation's existing `GUID` type pattern, `TRADEOS_DATABASE_DESIGN.md` §2.4) |
| Migrations | **Alembic** | MANDATORY (frozen — already named as in use by the reference implementation, `TRADEOS_DATABASE_DESIGN.md` §13.1) |
| Validation | **Pydantic v2** | MANDATORY (frozen — FastAPI's own native validation layer) |
| Authentication | **JWT via `python-jose`, `argon2-cffi` for password hashing** | MANDATORY (JWT frozen, `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-07; hashing algorithm per this document) |
| Authorization | **FastAPI `Depends()`-based ownership check, no external authz framework** | MANDATORY (this document) |
| Dependency Injection | **FastAPI's native `Depends()` system; constructor injection within Application-layer Use Cases** | MANDATORY (this document) |
| Background Jobs | **None selected — not applicable in v1** | N/A (frozen deferral, `TRADEOS_BACKEND_BLUEPRINT.md` §10) |
| Caching | **None selected — not applicable in v1** | N/A (frozen deferral, `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04) |
| Logging | **`structlog`, JSON-structured, correlation-ID bound** | MANDATORY (this document) |
| Configuration Management | **`pydantic-settings`, environment-variable-backed** | MANDATORY (this document) |

### 7.1 ORM — SQLAlchemy 2.0 (Async)
**Why selected:** `TRADEOS_DATABASE_DESIGN.md` Section 2.4 explicitly references "the existing reference implementation (`tradeos-backend`'s `GUID` type)" as the precedent for application-generated UUIDs — a `GUID` custom type is a well-established SQLAlchemy pattern (a `TypeDecorator`), confirming SQLAlchemy is already the reference implementation's ORM. This document makes that continuation explicit rather than silently assumed. SQLAlchemy 2.0's native async support pairs with FastAPI's async-first design (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8: "async-capable").
**Why it fits TradeOS specifically:** `TRADEOS_DATABASE_DESIGN.md` Section 7's config-driven Evaluation Engine storage (JSONB columns, e.g., `checklist_snapshots.answers`) is well supported by SQLAlchemy's native JSONB type mapping, without a second library.
**Alternatives considered:** Tortoise ORM — rejected as a smaller ecosystem with less battle-tested async/Alembic integration; raw SQL with `asyncpg` directly — rejected as forfeiting the Repository-pattern ergonomics `TRADEOS_BACKEND_BLUEPRINT.md` Section 6 already assumes, for no clear benefit at this project's scale.

### 7.2 Authentication — `python-jose` + Argon2id
**Why Argon2id, not bcrypt:** Argon2id is the current Password Hashing Competition-winning standard, offering better resistance to GPU/ASIC-based attacks than bcrypt. `TRADEOS_DATABASE_DESIGN.md` Section 11.1 deliberately names the column `password_hash`, not `password`, "to make misuse structurally awkward" — Argon2id is the modern default that column name's intent implies. bcrypt is not rejected as *unsafe*, only as no longer the preferred choice for new development (Section 16).
**Why `python-jose` for JWT:** a mature, widely adopted JWT/JOSE implementation for Python with no FastAPI-specific replacement that offers a clear advantage.

### 7.3 Authorization & Dependency Injection — FastAPI-Native, No External Framework
**Why selected:** `TRADEOS_API_SPECIFICATION.md` Section 4.6 already reduces the entire authorization model to a single ownership rule — there is no role/permission matrix to model (`TRADEOS_DOMAIN_MODEL.md` Section 3.4: Generic Domains get the least design effort). A `Depends()`-based ownership check, applied uniformly, fully implements that single rule. Introducing a policy engine (e.g., Oso, Casbin) or a dedicated DI container (e.g., `dependency-injector`) for a one-rule authorization model and a Clean Architecture already manually enforcing its own module boundaries (`TRADEOS_BACKEND_BLUEPRINT.md` Principle 6) would be disproportionate complexity (Section 5, Principle 2).

### 7.4 Logging — `structlog`
**Why selected:** `TRADEOS_BACKEND_BLUEPRINT.md` Section 11 requires every log line for a request to carry the same correlation ID, and requires Domain Events, business outcomes, and technical errors to be logged distinctly but consistently. `structlog`'s context-binding model (attach a correlation ID once, have it appear in every subsequent log call within that request) is a direct, idiomatic fit for that requirement, with structured (JSON) output suitable for any future log aggregation tool without this document needing to select one now.
**Alternatives considered:** Python's stdlib `logging` alone — viable but requires materially more boilerplate to achieve the same per-request context binding; `loguru` — a reasonable alternative, not selected because `structlog`'s structured-output-first design is a better match for the correlation-ID/JSON requirement specifically.

### 7.5 Configuration Management — `pydantic-settings`
**Why selected:** since Pydantic v2 is already mandatory (as FastAPI's own validation layer), `pydantic-settings` extends the same typed-model approach to environment-variable-backed configuration, directly satisfying `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1's "injected via environment configuration" with compile-time-checked config shapes rather than untyped `os.environ` lookups scattered through the codebase.

---

## 8. Database Stack

Every item in this section restates a decision already frozen in `TRADEOS_DATABASE_DESIGN.md` — this section exists so the Technical Stack document is a complete, single reference, not because any of it is newly decided here.

| Category | Official Choice | Frozen In |
|---|---|---|
| Database Engine | **PostgreSQL 16+** | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-06 (version floor per this document) |
| Migration Tool | **Alembic** | `TRADEOS_DATABASE_DESIGN.md` §13.1 |
| Backup Strategy | **The managed hosting platform's automated backup / point-in-time recovery** | Consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1's decision not to self-administer the database |
| Indexing Philosophy | **Indexes follow real, confirmed query shapes only — never speculative** | `TRADEOS_DATABASE_DESIGN.md` §10.1–10.2 |
| UUID Strategy | **Application-generated UUIDv4 for every primary key, except `scoring_criteria.id` (stable human-assigned string key)** | `TRADEOS_DATABASE_DESIGN.md` §2.4 |
| Soft Delete Policy | **Deactivation (`is_active`) for Catalog/Criteria/Weights; soft delete (`deleted_at`) for Trades/Journal/Playbook Setups; append-only/immutable for Snapshots and the event log** | `TRADEOS_DATABASE_DESIGN.md` §2.6 |
| Audit Fields | **`created_by_user_id` on every user-created row; `platform.event_log` as the durable Domain Event record** | `TRADEOS_DATABASE_DESIGN.md` §2.7 |
| Timestamp Strategy | **`TIMESTAMPTZ`, UTC, on every table; business timestamps (`entered_at`, `closed_at`) always distinct from audit timestamps (`created_at`, `updated_at`)** | `TRADEOS_DATABASE_DESIGN.md` §2.5 |

### 8.1 On the One New Decision in This Section — PostgreSQL Version Floor
**Why 16+:** `TRADEOS_DATABASE_DESIGN.md` Section 7 relies heavily on JSONB columns for the Evaluation Engine's config-driven storage. PostgreSQL 16 offers materially improved JSONB and general query-planner performance over older major versions with no compatibility cost, and is the most recent major version with a full production track record as of this document. This is a floor, not a ceiling — later major versions remain acceptable per the Versioning Policy (Section 17).

### 8.2 On Backup Strategy — No New Tool Selected
No frozen document names a specific backup tool, schedule, or RPO/RTO target. Rather than inventing one, this document defers to whatever automated backup capability the chosen managed hosting platform (Section 13) already provides — consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1's own reasoning for choosing a managed database in the first place ("to avoid spending effort on database operations that don't differentiate the product"). A specific RPO/RTO target is not defined here because no frozen document establishes an availability requirement precise enough to derive one from (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.4 states only that availability requirements are "modest").

---

## 9. Development Environment

| Category | Official Choice |
|---|---|
| Python Package Manager | **Poetry** |
| Node Package Manager | **pnpm** |
| Node Version | **Node 20 LTS+** |
| Repository Structure | **Two repositories: `tradeos-backend`, `tradeos-frontend`** |
| Environment Variables | **`.env` files locally (never committed), consumed via `pydantic-settings` (backend) and Vite's `import.meta.env` (frontend)** |
| Docker | **Mandatory for the backend; not used for local frontend development** |
| Docker Compose | **Mandatory for local dev — backend + PostgreSQL together** |

### 9.1 Package Managers — Poetry (Python), pnpm (Node)
**Why Poetry:** deterministic lockfile, unified dependency declaration and virtual-environment management in one tool, mature and well documented — preferred over plain `pip` + `requirements.txt` (weaker reproducibility guarantees without a lockfile) and over Pipenv (comparatively less active maintenance momentum).
**Why pnpm:** content-addressable storage makes installs materially faster and disk-efficient than npm, with strict, non-phantom dependency resolution that surfaces missing declared dependencies npm and Yarn Classic can silently hide — a direct Reliability benefit (Section 5, Principle 5) at negligible adoption cost.

### 9.2 Repository Structure — Two Repositories
**Why selected:** `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1 already establishes independent deployability — the frontend is "served independently of the backend." `PROJECT_AUDIT.md` Section 2 also confirms the project's existing artifacts (`tradeos-backend.zip`, `TradeOS_UI_v3.zip`) were already two separate codebases. This document preserves that existing, already-independent-deployment-aligned structure rather than consolidating into a monorepo, which would require new tooling (workspace orchestration) to solve a coordination problem that does not currently exist for a single deployable pair.

### 9.3 Docker & Docker Compose
**Why mandatory for the backend:** `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1 already requires "one containerized deployable" in production — using the same container locally (via Compose, alongside a local PostgreSQL container) guarantees dev/prod parity, directly serving Reliability (Section 5, Principle 5).
**Why not for the frontend:** the frontend's production artifact is a static build (Section 6.1), not a running container — Vite's own dev server is the correct local-development tool, and containerizing it would add no parity benefit since nothing about it changes between a container and a bare process.

---

## 10. Testing Stack

Every choice below operationalizes `TRADEOS_BACKEND_BLUEPRINT.md` Section 15 (Testing Blueprint) and `TRADEOS_FRONTEND_BLUEPRINT.md`'s implicit testing needs — neither document names specific tools, only test *categories* and *philosophy*, which this section now assigns tools to.

| Test Level | Official Tool | Rationale Summary |
|---|---|---|
| Backend Unit Testing | **pytest** | Already frozen (`TRADEOS_SYSTEM_ARCHITECTURE.md` §8) |
| Frontend Unit Testing | **Vitest** | Native Vite integration (Section 6.1); Jest-API-compatible, faster |
| Integration Testing | **pytest + Testcontainers (real PostgreSQL in CI)** | Matches `TRADEOS_BACKEND_BLUEPRINT.md` §15's "tested end-to-end against a real... database" |
| End-to-End Testing | **Playwright** | Modern, multi-browser, strong TypeScript support |
| API/Contract Testing | **pytest + FastAPI's `TestClient`/`httpx`** | No separate tool needed — verifies `TRADEOS_API_SPECIFICATION.md` §6 shapes directly |
| Test Coverage Expectations | **Domain layer (Evaluation especially): every Domain Invariant has a named test. Application layer: one test per success/failure path (`TRADEOS_BACKEND_BLUEPRINT.md` §4). Infrastructure/Presentation: contract-focused, pragmatic.** | Restates `TRADEOS_BACKEND_BLUEPRINT.md` §15 exactly — no new numeric coverage threshold is invented beyond what that section already states qualitatively |

### 10.1 Why Playwright, Not Cypress
Playwright supports genuinely parallel, multi-browser test execution (Chromium, Firefox, WebKit) from one test file, has first-class TypeScript support matching the frontend's own language choice (Section 6), and — unlike Cypress at the time of this document — runs outside the browser process, avoiding a category of test flakiness Cypress's in-browser architecture is more prone to. Cypress remains a mature, viable tool; Playwright is preferred here on ecosystem trajectory and multi-browser support specifically (Section 16).

### 10.2 Why Testcontainers for Integration Tests
Spinning up a real, ephemeral PostgreSQL instance per test run (rather than mocking the database or relying on a shared, hand-maintained test database) directly serves `TRADEOS_BACKEND_BLUEPRINT.md` Section 15's explicit standard: Repository and Use Case tests must verify real transaction behavior, not just Domain logic in isolation. This is the mechanism, not a new decision — the standard itself is already frozen.

---

## 11. Code Quality

| Category | Official Choice |
|---|---|
| Backend Formatter & Linter | **Ruff** (format + lint, unified) |
| Backend Type Checking | **mypy** |
| Frontend Formatter | **Prettier** |
| Frontend Linter | **ESLint** (with `eslint-plugin-jsx-a11y` for accessibility) |
| Frontend Type Checking | **TypeScript compiler (`tsc --noEmit`)** |
| Commit Standard | **Conventional Commits** |
| Branch Strategy | **Trunk-based development (GitHub Flow): `main` + short-lived feature branches + PR** |
| Pull Request Expectations | **Every change goes through a PR, even for a single contributor; the PR description names the Implementation Master Plan phase/sprint and the Domain Invariants (if any) it touches** |

### 11.1 Backend — Ruff (Formatter + Linter)
**Why selected:** Ruff consolidates what previously required three separate tools (Flake8 for linting, isort for import ordering, Black for formatting) into one, dramatically faster tool with active, mature maintenance. Fewer tools in the pipeline is a direct Maintainability win (Section 5, Principle 3) with no functional trade-off — its rule set is a superset covering the same ground as the tools it replaces.
**Alternatives considered:** Black + isort + Flake8 separately — rejected only because Ruff now covers the same ground in one faster, simpler-to-configure tool; not rejected as inferior in output quality.

### 11.2 Backend — mypy
**Why selected over Pyright:** mypy remains the longest-standing, most broadly plugin-supported static type checker in the Python ecosystem, with the widest base of community troubleshooting documentation (Section 5, Principles 5–6) — directly relevant for a project maintained by one person. Pyright is faster and used by VS Code's Pylance, a genuine advantage, but not enough to outweigh mypy's maturity and CI-configuration stability for this project's scale.

### 11.3 Frontend — Prettier + ESLint
**Why selected over Biome:** Biome is a newer, faster, Rust-based alternative unifying formatting and linting (the JS/TS analogue of Ruff, Section 11.1) — but as of this document, it has a materially shorter track record and thinner plugin ecosystem than the Prettier + ESLint combination, specifically for the accessibility linting (`eslint-plugin-jsx-a11y`) `TRADEOS_FRONTEND_BLUEPRINT.md` Section 15 requires. Prettier + ESLint is chosen for ecosystem maturity (Section 5, Principle 5) today; Biome is not rejected outright — see Section 16 for its status as a documented, revisitable choice rather than a permanently closed one.

### 11.4 Commit & Branch Conventions
**Why Conventional Commits:** every one of the nine prior canonical documents already maintains a rigorous, versioned Change Log / Document Control table. Conventional Commits (`feat:`, `fix:`, `chore:`, etc.) extends that exact same discipline — a legible, structured history — down to the level of individual code commits, and mechanically enables future changelog generation without new tooling invention.
**Why trunk-based over GitFlow:** GitFlow's release-branch/hotfix-branch model is designed to coordinate multiple teams shipping on different cadences — disproportionate ceremony for the single confirmed maintainer this project has today (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2; Section 5, Principle 2 here). Trunk-based development with short-lived feature branches keeps the same safety (CI gate on every PR) at a fraction of the process overhead.

---

## 12. CI/CD

| Category | Official Choice |
|---|---|
| CI/CD Platform | **GitHub Actions** |
| Build Pipeline | Backend: install (Poetry) → Ruff format-check → mypy → build Docker image. Frontend: install (pnpm) → `tsc --noEmit` → Vite build. |
| Test Pipeline | Backend: pytest (unit + integration, via Testcontainers) on every PR. Frontend: Vitest on every PR. Playwright E2E on merge to `main` (and nightly). |
| Lint Pipeline | Ruff + mypy (backend), ESLint + Prettier check + `tsc` (frontend) — every PR, blocking merge on failure. |
| Release Strategy | Semantic versioning for the backend container image and the frontend build artifact; automatic deploy to staging on merge to `main`; production deploy behind a manual approval gate. |

### 12.1 Why GitHub Actions
No frozen document names a code-hosting platform or CI provider. GitHub Actions is selected here as the standard on the basis of ecosystem maturity, native integration with the repository host it's overwhelmingly likely to be paired with, and zero additional infrastructure to operate — consistent with Section 5's Maintainability and Mature Ecosystem principles. If a different code host is later adopted, only this pipeline's YAML definitions require re-targeting, not any application code (Section 5, Principle 8, Incremental Evolution) — see Open Question OQ-8 (Section 20) for the underlying, never-formally-confirmed assumption this rests on.

### 12.2 Why a Manual Approval Gate for Production
`TRADEOS_PRODUCT_BIBLE.md` NFR 10.4 confirms availability requirements are "modest" for a single-user system with "no fixed uptime guarantee beyond not losing data" — this is the lowest-risk, lowest-tooling-cost way to prevent an unreviewed change from reaching production, appropriate to that same modest-availability, single-maintainer context (Section 5, Principle 2).

### 12.3 Current implementation status (Sprint 9.4, `CHANGELOG.md`)
A documented **subset** of the Build/Test/Lint Pipeline rows above is now implemented, as three separate GitHub Actions workflows (`.github/workflows/backend-ci.yml`, `frontend-ci.yml`, `container-scan.yml`): install → lint → type-check → unit/integration tests → build, on every push and pull request, each scoped to its own `paths` filter. **Not yet implemented, still exactly as originally described above:** the Playwright E2E stage, the automatic staging deploy, and the manual-approval production gate — none of those were in this sprint's approved scope (`CHANGELOG.md`, Sprint 9.4: "Render deployment, Auto Deploy, Staging, Production deployment" explicitly excluded). This is an implementation-status note, not a change to the Build/Test/Lint Pipeline decisions themselves.

All three workflows follow `GITHUB_TOKEN` least privilege (GitHub's own Security Hardening Guide for GitHub Actions) and declare only `contents: read` — no workflow is granted write access to repository contents. `container-scan.yml` does **not** upload to GitHub's Security tab: this is a private repository owned by a personal account, and GitHub Code Security/Advanced Security (upload-sarif's real requirement) is only purchasable on a GitHub Team or Enterprise plan, confirmed both by official documentation and empirically (`gh api repos/.../code-scanning/alerts` returns 403 "Code scanning is not enabled for this repository"). Trivy's SARIF report is instead uploaded as a plain workflow artifact (`actions/upload-artifact`), which needs no additional permission or license.

---

## 13. Deployment Targets

Per this document's own mandate (Section 4) and the user's explicit instruction, **no specific cloud provider is chosen here** — `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1 commits only to a *class* of managed platform, and this document preserves exactly that level of commitment. **Render was operationally selected within this class in Sprint 9.2** (`CHANGELOG.md`; `render.yaml` at the repo root) — the table below still describes the class-level commitment this document is scoped to, not a rewrite of it; `render.yaml` is the concrete, currently-in-use instantiation of the "Production" row for whichever fields Render specifically requires (`dockerCommand`, `healthCheckPath`, `preDeployCommand`).

| Environment | Target |
|---|---|
| **Local Development** | Docker Compose (backend container + PostgreSQL container); Vite dev server for the frontend, run as a bare process, not containerized (Section 9.3). |
| **Staging** | A second instance of the same containerized backend + a second managed PostgreSQL instance, on the same class of managed platform as production (`TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1 — "a Railway/Fly.io/Render-equivalent"). No specific vendor is named by this document. |
| **Production** | The containerized backend and a managed PostgreSQL instance on that same platform class; the frontend's static build served by any static-hosting-capable service of that same class — again, no specific vendor named here, consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1's own restraint. |

**Explicitly conditional (restated, not redecided):** `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.2 already states that this entire deployment shape is sized for "one user, personal use" and must be explicitly revisited — not silently stretched — if Product Bible Open Question 2 (business model) resolves toward offering TradeOS to other traders. This document does not alter that condition.

---

## 14. Security Tooling

| Category | Official Choice |
|---|---|
| Secret Management | **The hosting platform's built-in environment-variable/secret store** — no dedicated secrets manager (e.g., Vault) in v1 |
| Dependency Scanning | **Dependabot** (GitHub-native) |
| Vulnerability Scanning | **`pip-audit`, `pnpm audit`, and Trivy (container image scanning)** |
| Security Headers | **Standard baseline set** (`Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`, `X-Content-Type-Options`), applied at the static-hosting layer (frontend) and via lightweight middleware (backend) |
| HTTPS Requirements | **TLS mandatory everywhere, no exceptions** |

### 14.1 Why No Dedicated Secrets Manager
`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1 requires only that secrets are "never committed to source control and are injected via environment configuration" — it does not require a dedicated secrets-management product. Introducing one (Vault, AWS Secrets Manager) now would be disproportionate to the confirmed single-user scale (Section 5, Principle 2) and is explicitly deferred, to be revisited only if `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.2's still-open security posture questions (encryption at rest, staff data access) resolve toward a scale that needs it.

### 14.2 Why Dependabot + `pip-audit`/`pnpm audit` + Trivy
All three are free, natively integrated with the already-selected GitHub Actions pipeline (Section 12), require no separate account or infrastructure, and directly serve `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9's Security ranking (#5, above Performance/Scalability) at negligible operational cost — consistent with Section 5's principle that tool selection should not require effort disproportionate to the problem it solves.

### 14.3 HTTPS — Restated, Not New
`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1 already states TLS is "not optional, not deferred." This section adds no new requirement — it exists only so this document is a complete reference without requiring a cross-reference for this one fact.

### 14.4 Current implementation status (Sprint 9.4, `CHANGELOG.md`)
Dependency Scanning and Vulnerability Scanning — **resolved, no longer only chosen-but-unimplemented.** `.github/dependabot.yml` covers all four ecosystems this repository has (`pip`, `npm`, `docker`, `github-actions`); `pip-audit`, `pnpm audit`, and Trivy now run as steps of `backend-ci.yml`/`frontend-ci.yml`/`container-scan.yml` respectively. This was previously blocked on Open Question OQ-8 (Section 20) — now resolved. Trivy and `pnpm audit` fail their build on `CRITICAL`/`HIGH` findings (the officially documented example configuration for each tool — see `CHANGELOG.md`, Sprint 9.4, for the full citation trail); `pip-audit` runs report-only, since it has no severity filter of its own to calibrate against the same threshold (confirmed against its own documentation: no `--min-severity` option exists), and blocking on any finding today would fail on vulnerabilities already present in dependencies before this sprint, unrelated to it. Security Headers and HTTPS Requirements: unchanged, already implemented in Sprint 9.3. Secret Management: unchanged, §14.1's reasoning still holds.

---

## 15. Performance Guidelines

**This section defines engineering standards only, per this document's own mandate (Section 4) — it does not redesign any system behavior already frozen upstream.**

- **Backend:** every Repository method's query shape must match an index already specified in `TRADEOS_DATABASE_DESIGN.md` Section 10.1 — a new query against an unindexed access pattern is a code-review-blocking defect, not a follow-up task. Single-row, single-transaction writes throughout (`TRADEOS_BACKEND_BLUEPRINT.md` Section 9) — no write batching is introduced without a demonstrated need.
- **Frontend:** lazy-load feature modules per Vite's code-splitting (Section 6.1), matching `TRADEOS_FRONTEND_BLUEPRINT.md` Section 16's per-feature bundle boundary; virtualize the Trades table unconditionally (Section 6.9) given the confirmed 20,000+ trade target.
- **Analytics:** Statistics remains computed-on-demand, never cached, per `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04 — this document introduces no caching technology (Section 7) precisely to avoid silently reopening that decision.
- **CI enforcement:** the test and lint pipelines (Section 12) are the mechanism that makes these standards checkable rather than aspirational — a PR that introduces an unindexed query pattern or an un-virtualized large table should be caught in review, not discovered in production.

---

## 16. Technologies Explicitly Rejected

| Technology | Rejected In Favor Of | Reason |
|---|---|---|
| Next.js | Vite (Section 6.1) | Default SSR/API-route model contradicts the static-hosting, no-secondary-backend decision already frozen (`TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1; `TRADEOS_FRONTEND_BLUEPRINT.md` §2.1) |
| Create React App | Vite | Deprecated by its own ecosystem; no longer a mature, actively maintained choice |
| Redux, Zustand (as default) | React Context/local state (Section 6.3) | `TRADEOS_FRONTEND_BLUEPRINT.md` §2.5 already scopes UI state as component/feature-local; a global store is unjustified complexity |
| styled-components / Emotion | Tailwind CSS (Section 6.6) | Runtime CSS-in-JS cost cuts against performance guidance (`TRADEOS_FRONTEND_BLUEPRINT.md` §16); weaker fit with the Radix headless-component foundation |
| Moment.js | date-fns (Section 6.10) | Legacy, mutable-date API, in maintenance mode by its own authors' recommendation |
| Cypress | Playwright (Section 10.1) | Weaker multi-browser parallelism and TypeScript-first ergonomics for this project's needs; a viable tool, not an unsafe one |
| GraphQL, gRPC | REST/JSON (already frozen) | `TRADEOS_API_SPECIFICATION.md` §3.1 and `TRADEOS_SYSTEM_ARCHITECTURE.md` §8 already confirm REST; no new client requirement justifies reopening this |
| Microservices | Modular Monolith (already frozen) | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-01 — restated here only to confirm this document does not reopen it |
| A dedicated DI container (e.g., `dependency-injector`) | FastAPI-native `Depends()` (Section 7.3) | Disproportionate to a Clean Architecture already manually enforcing module boundaries |
| A dedicated authorization framework (Oso, Casbin) | FastAPI-native ownership check (Section 7.3) | The entire authorization model is one rule (`TRADEOS_API_SPECIFICATION.md` §4.6) — a policy engine solves a problem this project does not have |
| Vault / AWS Secrets Manager | Hosting platform's built-in secret store (Section 14.1) | Disproportionate to confirmed single-user scale; revisit only if scale changes |
| A named cloud provider | A managed-platform *class* (Section 13) | No frozen document requires naming a specific vendor; this document preserves that same restraint |
| GitFlow | Trunk-based development (Section 11.4) | Coordination overhead designed for multi-team cadences this single-maintainer project does not have |
| bcrypt (for new development) | Argon2id (Section 7.2) | Not unsafe, but no longer the preferred modern default this document standardizes on |
| MongoDB / any NoSQL store | PostgreSQL (already frozen) | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-06 — restated here only for completeness |
| Biome | Prettier + ESLint (Section 11.3) | Thinner ecosystem/plugin maturity today, specifically for accessibility linting; a documented, revisitable choice, not a permanent rejection |

---

## 17. Versioning Policy

| Component | Supported Major Version(s) | Upgrade Policy |
|---|---|---|
| Python | 3.12+ | Minor/patch versions adopted promptly via Dependabot; a new major version is adopted only after the full test suite (Section 10) passes against it |
| Node.js | 20 LTS+ | Track LTS releases only; never adopt an odd-numbered (non-LTS) release for anything but local experimentation |
| PostgreSQL | 16+ | Major version upgrades planned deliberately, never performed as a side effect of an unrelated change; always tested against Section 10's integration suite first |
| FastAPI | Latest stable release line | Tracked closely given this project's single-maintainer capacity to absorb minor API changes promptly; a breaking FastAPI release is reviewed before adoption, never auto-merged |
| React | 18+ | Adopt new major versions only after confirming Radix UI, TanStack Query/Table, and React Hook Form (Section 6) all officially support it |
| **Dependency Review Policy** | — | Dependabot PRs (Section 14) are reviewed at least monthly for patch/minor bumps; any major-version bump requires (1) the full test suite passing, and (2) a one-line note in the PR of what changed and why it's safe — extending `TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 8 ("Every Decision Is Traceable") to dependency upgrades specifically. |

---

## 18. Implementation Readiness Checklist

Claude Code verifies every item below before writing production code for any phase named in `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`:

- [ ] Python 3.12+ and Node 20 LTS+ are installed and match the versions pinned in `pyproject.toml` / `package.json`.
- [ ] Poetry's `poetry.lock` and pnpm's `pnpm-lock.yaml` are both committed and up to date with their respective manifest files.
- [ ] `docker compose up` brings up the backend container and a PostgreSQL 16+ container with no manual intervention.
- [ ] `alembic upgrade head` applies cleanly with no unresolved multiple-head conflicts.
- [ ] Ruff (`ruff format --check`, `ruff check`) and mypy both pass with zero errors on a clean checkout.
- [ ] ESLint, Prettier (`--check`), and `tsc --noEmit` all pass with zero errors on a clean checkout.
- [ ] The full pytest suite (unit + integration, via Testcontainers) passes locally against a freshly seeded database.
- [ ] The full Vitest suite passes.
- [ ] Every required environment variable is documented in a checked-in `.env.example`; no real secret value is committed anywhere in the repository.
- [ ] The CI pipeline (Section 12) is green on the target branch before merge.
- [ ] The specific canonical document section(s) that justify the feature about to be built have been re-read — cross-checked against `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Section 14's Traceability Matrix for the relevant phase.
- [ ] Any new gap or ambiguity discovered while implementing is registered as a Known Gap or Open Question in the relevant document — never silently resolved in code alone.

---

## 19. Traceability Matrix

| Stack Category | Official Choice | Justified/Required By |
|---|---|---|
| Frontend framework & language | React + TypeScript | `TRADEOS_SYSTEM_ARCHITECTURE.md` §8, §8.5 |
| Frontend build/hosting model | Vite, static hosting | `TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1; `TRADEOS_FRONTEND_BLUEPRINT.md` §2.1 |
| Frontend state split | TanStack Query / React Context | `TRADEOS_FRONTEND_BLUEPRINT.md` §2.5, §2.7 |
| Frontend accessibility foundation | Radix UI Primitives | `TRADEOS_FRONTEND_BLUEPRINT.md` §15 |
| Frontend table virtualization | TanStack Table + Virtual | `TRADEOS_FRONTEND_BLUEPRINT.md` §16; `TRADEOS_PRODUCT_BIBLE.md` NFR 10.2 |
| Backend framework & language | FastAPI + Python | `TRADEOS_SYSTEM_ARCHITECTURE.md` §8 |
| Backend ORM & migrations | SQLAlchemy 2.0 + Alembic | `TRADEOS_DATABASE_DESIGN.md` §2.4, §13.1 |
| Authentication | JWT (token-based) | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-07; `TRADEOS_API_SPECIFICATION.md` §4 |
| Authorization model | Single ownership rule, FastAPI `Depends()` | `TRADEOS_API_SPECIFICATION.md` §4.6 |
| Database engine | PostgreSQL 16+ | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-06 |
| UUID / soft-delete / timestamp / audit strategy | (Section 8 table) | `TRADEOS_DATABASE_DESIGN.md` §2.4–2.7 |
| Testing philosophy & coverage bar | pytest, Vitest, Playwright, Testcontainers | `TRADEOS_SYSTEM_ARCHITECTURE.md` §8 (testing row); `TRADEOS_BACKEND_BLUEPRINT.md` §15 |
| Event dispatch mechanism | In-process, synchronous (unchanged) | `TRADEOS_SYSTEM_ARCHITECTURE.md` §6.1, ADR-05 |
| Deployment platform class | Managed platform, class-level only | `TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1 |
| Security baseline | TLS mandatory, secrets via env vars | `TRADEOS_SYSTEM_ARCHITECTURE.md` §11.1 |
| No caching / no background jobs in v1 | None selected | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04; `TRADEOS_BACKEND_BLUEPRINT.md` §10 |
| Implementation sequencing this document assumes | 10-phase order | `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §6, §8 |

---

## 20. Open Questions

Filtered strictly to genuinely unresolved technical decisions — every other choice in this document is a final, official selection, not a placeholder.

| ID | Question | Why It's Genuinely Open |
|---|---|---|
| OQ-5 | What exact Python patch/minor version does the existing reference implementation (`tradeos-backend`) currently target? | No frozen document pins one — this document recommends a floor (3.12+, Section 17) but cannot confirm the reference code's actual current interpreter version without inspecting it directly |
| OQ-6 | What object storage provider holds Playbook Setup attachment files? | `TRADEOS_DATABASE_DESIGN.md` Section 6.16 confirms the *pattern* (a reference/key stored in Postgres, the file itself in "object storage") but names no specific provider or service — this document's file-upload approach (Section 6.12) is provider-agnostic until this resolves |
| OQ-7 | Where does a user's display timezone come from — browser-detected, or a stored `Preferences` field? | `TRADEOS_DOMAIN_MODEL.md` Section 8.12 names theme/language/notification/display preferences but no explicit timezone field; local-time display of `entered_at`/`closed_at` (Section 6.10) cannot be fully implemented until this is decided |

**OQ-8 — resolved, Sprint 9.4 (`CHANGELOG.md`):** GitHub is the confirmed code-hosting platform. Verified directly against this repository's own configuration — `git remote -v` returns `origin git@github.com:Jaiderrtriana/TradeOS.git` for both fetch and push — rather than inferred or assumed. This confirms the "most likely default" Section 12.1 and Section 14.2 already assumed, and unblocks both: the GitHub Actions CI/CD pipeline (Section 12.3) and Dependabot plus the vulnerability scanners (Section 14.4) are now implemented on that confirmed basis.

---

## 21. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-25 | Initial Technical Stack. Restated all previously-frozen technology decisions (FastAPI, Python, PostgreSQL, React + TypeScript, REST/JSON, JWT, pytest, Alembic) without alteration. Made one official, justified selection per open tooling category across frontend, backend, database, development environment, testing, code quality, CI/CD, deployment target class, and security tooling — always exactly one standard per category, with alternatives explicitly named and rejected rather than left as equivalent options. Registered four genuine Open Questions (OQ-5 through OQ-8) rather than inventing answers. Introduced no caching, background-job, or messaging technology, consistent with those capabilities' continued upstream deferral. |
| 1.1 | 2026-08-07 | Sprint 9.4 (Deployment Readiness & Operational Hardening). Section 20: resolved OQ-8 (GitHub confirmed as code-hosting platform, verified via `git remote -v`). Section 12: recorded implementation status of a documented subset of the CI/CD pipeline (lint/type-check/test/build via three separate GitHub Actions workflows; E2E, staging auto-deploy, and the production approval gate remain future work). Section 14: recorded implementation status of Dependency/Vulnerability Scanning (Dependabot, `pip-audit`, `pnpm audit`, Trivy) — all now wired into that same CI, unblocked by OQ-8's resolution. No technology selection already made in this document was altered by either change. |

**Status:** FROZEN. This is the tenth document of TradeOS. It contains no architectural, domain, or business decision of its own — only the official, justified tooling standard for implementing the nine documents that precede it.
