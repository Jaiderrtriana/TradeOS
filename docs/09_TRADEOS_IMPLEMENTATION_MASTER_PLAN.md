# 09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md

**Document Status:** CANONICAL AND FROZEN — the official implementation roadmap of TradeOS.
**Version:** 1.0
**Last Updated:** 2026-07-25
**Depends On:** all eight prior frozen documents — `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md` v2.1, `TRADEOS_DOMAIN_MODEL.md` v1.1, `TRADEOS_SYSTEM_ARCHITECTURE.md` v1.2, `TRADEOS_DATABASE_DESIGN.md` v1.1, `TRADEOS_API_SPECIFICATION.md` v1.1, `TRADEOS_FRONTEND_BLUEPRINT.md` v1.1, `TRADEOS_BACKEND_BLUEPRINT.md` v1.1 (all frozen).
**Redesigns:** nothing. This document introduces no business rule, no domain concept, no table, no endpoint, no page, and no module boundary that is not already named in one of the eight documents above. Every phase, sprint, and milestone below is a *sequencing and packaging* decision, never a *design* decision.
**Is Not:** a ninth architecture document. Where this document appears to make a judgment call, that judgment is either (a) a direct, cited restatement of the Backend Blueprint's own Implementation Readiness Assessment (`TRADEOS_BACKEND_BLUEPRINT.md` Section 20) and the Frontend Blueprint's own module/page structure, or (b) explicitly registered as an Open Question (Section 16) or Known Gap (Section 15) rather than silently resolved.
**Audience:** Claude Code, executing this plan phase by phase, sprint by sprint, against the seven upstream frozen documents as its only source of business/technical truth. This document tells Claude Code *what to build when and in what order*; it never tells Claude Code *what the system is* — that question is always answered by looking upstream.

---

## 1. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-25 | Initial Implementation Master Plan. Derived from all eight frozen foundational documents, principally `TRADEOS_BACKEND_BLUEPRINT.md` Section 20 (Implementation Readiness Assessment) and `TRADEOS_FRONTEND_BLUEPRINT.md` Sections 3–5 (Application Structure, Navigation, Page Blueprint), reading their existing module ordering, dependencies, and status forward into a full dependency graph, phase/sprint breakdown, testing strategy, milestone set, Definition of Done, risk register, consolidated (frontend + backend) readiness matrix, traceability matrix, and a filtered set of genuinely implementation-blocking Open Questions. Reports, AI Coaching, Notifications, and Broker/Exchange Integration were excluded as phases because no frozen document confirms a Domain Model entity, database table, or API module for any of them (`TRADEOS_API_SPECIFICATION.md` Section 18; `TRADEOS_DATABASE_DESIGN.md` Section 14; `TRADEOS_BACKEND_BLUEPRINT.md` Sections 3.11, 3.13) — they are carried forward as Future Enhancements (Section 17) only. |

**Status:** FROZEN. This is the ninth document of TradeOS, after `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`, `TRADEOS_API_SPECIFICATION.md`, `TRADEOS_FRONTEND_BLUEPRINT.md`, and `TRADEOS_BACKEND_BLUEPRINT.md`.
**Next document:** to be determined — candidates named in Section 16 (Open Questions) should be resolved, at the appropriate upstream document, before or during Phase 9 (Deployment).

---

## 2. Purpose

The eight prior documents answer *what TradeOS is* and *how it is architected* — business rules, domain model, system architecture, schema, API contract, and frontend/backend blueprints. None of them answers *in what order to build it, in what increments, with what tests, and against what completion criteria* — that is this document's entire purpose.

This document exists so that Claude Code can execute the approved architecture without re-deriving sequencing decisions from first principles on every session, and so that "what should be built next" has one authoritative answer instead of being re-litigated per conversation. It is the operational bridge between an approved design and running, tested software.

---

## 3. Scope

This document defines, for the entire TradeOS v1 build:

- A complete module dependency graph (Section 5).
- A justified implementation order (Section 6).
- Milestones marking real, demonstrable progress (Section 7).
- Logical phases, each scoped to a Bounded Context or a cross-cutting concern already named upstream (Section 8).
- Sprint-level breakdowns with objectives, deliverables, dependencies, and exit criteria (Section 9).
- A per-phase testing strategy across unit/integration/E2E/regression levels (Section 10).
- A measurable Definition of Done, both generally and per phase (Section 11).
- An implementation risk register grounded in this project's own documented history (Section 12).
- A consolidated (frontend + backend + API + database) implementation readiness matrix (Section 13).
- Full traceability from every phase back to the eight canonical documents (Section 14).
- Known implementation gaps carried forward (Section 15) and a filtered list of genuinely blocking Open Questions (Section 16).
- An explicit boundary between this v1 plan and everything reserved for later (Section 17).

---

## 4. Out of Scope

This document does not, and per its own mandate must not:

- Redesign, reinterpret, or extend the Domain Model, System Architecture, Database Design, API Specification, or Frontend/Backend Blueprints. Any apparent gap in one of those documents is registered here (Section 15/16), never patched here.
- Resolve any Product Bible Open Foundational Question (`TRADEOS_PRODUCT_BIBLE.md` Section 15) or any Domain Model / Database Design / API Specification / Frontend / Backend open item on its own authority. Where an unresolved question genuinely blocks a phase, it is named in Section 16 as a blocker, not answered.
- Plan implementation for **Reports**, **AI Coaching**, **Notifications**, or **Broker/Exchange Integration** — all four are, without exception across every upstream document, reserved namespaces with no confirmed Domain Model entity, database table, or API endpoint (`TRADEOS_DOMAIN_MODEL.md` Section 17; `TRADEOS_DATABASE_DESIGN.md` Section 12; `TRADEOS_API_SPECIFICATION.md` Section 17; `TRADEOS_BACKEND_BLUEPRINT.md` Sections 3.11, 3.13). They appear only in Section 17 (Future Enhancements).
- Plan for multi-user, multi-tenant, or team-workspace scope. Every phase below assumes the single confirmed user (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2) that every upstream document already assumes.
- Choose a specific hosting provider, CI/CD vendor, background-job technology, or observability tool. `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8.4 and `TRADEOS_BACKEND_BLUEPRINT.md` Section 10 both leave these as implementation-time choices within an already-approved category (e.g., "a managed Railway/Fly.io/Render-equivalent platform") — this document sequences *when* that choice is made, never *what* it is.
- Estimate calendar time or effort in days/weeks. `TRADEOS_BACKEND_BLUEPRINT.md` Section 20 explicitly states its own ordering "reflects dependency structure only... not effort estimation" — this document inherits that same restraint. "Estimated Implementation Order" and "Sprint" here are sequencing units, not time-boxes.

---

## 5. Dependency Graph

This graph merges `TRADEOS_BACKEND_BLUEPRINT.md` Section 20's module dependency column with `TRADEOS_DOMAIN_MODEL.md` Section 5's Context Map and `TRADEOS_FRONTEND_BLUEPRINT.md` Section 3's 1:1 frontend-to-API module mapping. An arrow means "the thing being pointed to must exist, at least in a minimally usable form, before the thing pointing to it can be meaningfully built and tested."

```
                         ┌─────────────────────────────┐
                         │  Infrastructure / Platform  │  (event dispatcher, auth
                         │      (Backend §3.12)        │   middleware, event_log,
                         └──────────────┬──────────────┘   correlation IDs)
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
         ┌───────────────┐     ┌───────────────┐      ┌────────────────┐
         │    Identity   │────▶│  Preferences  │      │ Configuration  │
         │ (Auth/Users)  │     │  (Settings)   │      │ (+ Catalogs,   │
         └───────┬───────┘     └───────────────┘      │  same module)  │
                 │                                     └────────┬───────┘
                 │  (user_id ownership on every                 │
                 │   downstream aggregate)                      │ supplies criteria,
                 │                                               │ weights, profiles,
                 │                                               │ catalog entries
                 │                                               ▼
                 │                                     ┌────────────────┐
                 │                                     │   Evaluation   │  (Core Domain;
                 │                                     │ (5 engines)    │   no persistence
                 │                                     └────────┬───────┘   of its own)
                 │                                              │ synchronous, same-
                 │                                              │ transaction call
                 │                                              ▼
                 │                                     ┌────────────────┐
                 └────────────────────────────────────▶│    Trading     │  (Trade,
                        owns every Trade                │ (Trades, MFE/  │   Checklist,
                                                         │  MAE, Mistake  │   EvaluationSnapshot)
                                                         │  tagging)      │
                                                         └───┬───────┬────┘
                                        ┌──────────────────-┘       └───────────────┐
                                        ▼                                          ▼
                              ┌────────────────┐                          ┌────────────────┐
                              │    Journal     │                          │   Mistakes     │
                              │ (trade-scoped  │                          │ (read-only     │
                              │  or period-    │                          │  ranking; also │
                              │  scoped)       │                          │  needs         │
                              └────────────────┘                          │  Catalogs)     │
                                                                           └────────────────┘
                                        Trading + Evaluation
                                                │
                                                ▼
                                      ┌────────────────┐
                                      │  Statistics    │  (Analytics; no
                                      │  (Analytics)   │   persistence of its own)
                                      └───────┬────────┘
                                              │ StatisticsAggregationService
                                              ▼
                                      ┌────────────────┐
                                      │   Playbook     │  (also needs Catalogs
                                      │                │   for its Setup reference)
                                      └───────┬────────┘
                                              │
                    Trading + Statistics + Playbook (composition only)
                                              ▼
                                      ┌────────────────┐
                                      │   Dashboard    │  (not a Bounded Context —
                                      │  (composition) │   API Spec §5.1)
                                      └───────┬────────┘
                                              │
                                              ▼
                                      ┌────────────────┐
                                      │   Deployment   │  (containerize, provision
                                      │  & Hardening   │   DB, static-host frontend,
                                      │                │   TLS, secrets)
                                      └────────────────┘

Reserved, no edges into the graph above (excluded from this plan — Section 4, Section 17):
  Reports · AI Coaching · Notifications · Broker/Exchange Integration
```

### 5.1 Frontend Dependency Overlay

Per `TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.4 ("Feature-first, mirroring the backend's module-first organization"), every frontend feature module depends on its corresponding backend/API module reaching at least a callable state first — the frontend for a module is never scheduled ahead of that module's API. The one exception is the **application shell** (routing, API client layer, design system tokens, auth-aware layout), which has no Bounded Context of its own and is built once, in Phase 0, ahead of every feature module (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 2.1–2.2).

### 5.2 Why This Shape

- **Configuration is the most upstream Bounded Context** (`TRADEOS_DOMAIN_MODEL.md` Section 4.3: "Configuration is upstream of Evaluation") — nothing that depends on a Score can be meaningfully tested until Configuration exists and is seeded.
- **Evaluation sits between Configuration and Trading** because Trading's `RegisterTrade` Use Case calls Evaluation synchronously, in the same transaction, before a Trade is considered saved (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4, ADR-03; `TRADEOS_BACKEND_BLUEPRINT.md` Section 4.1) — Trading cannot be exercised end-to-end without a working Evaluation module behind it.
- **Analytics (Statistics) and Playbook are downstream of Trading + Evaluation** because both are pure read-side computations over Trading/Evaluation data (`TRADEOS_DOMAIN_MODEL.md` KDD-04) — there is nothing to aggregate until real Trade + Evaluation data exists.
- **Dashboard is last among the feature modules** because it is a pure composition over Statistics + Trades (`TRADEOS_API_SPECIFICATION.md` Section 5.1) and has no independent capability of its own.
- **Deployment is last overall** because it hardens and ships what every prior phase already built — it is not a phase that produces new business capability.

---

## 6. Implementation Order

Justified strictly by the dependency graph (Section 5) and by `TRADEOS_BACKEND_BLUEPRINT.md` Section 20's own "Estimated Implementation Order" column, which this document adopts rather than re-derives:

| Order | Phase | Primary Modules | Why This Position (Dependency Reasoning) |
|---|---|---|---|
| 0 | Infrastructure & Platform | Platform, frontend app shell | Nothing downstream is meaningfully testable without the event dispatcher, `platform.event_log`, auth middleware, and the frontend's API client layer already existing (`TRADEOS_BACKEND_BLUEPRINT.md` §20, row 1). |
| 1 | Identity & Preferences | Identity, Preferences | Every other aggregate carries a `user_id` (`TRADEOS_DATABASE_DESIGN.md` §11.2) — ownership cannot be enforced against a user that doesn't yet exist. Preferences is trivial and safe to build alongside Identity, not strictly after (`TRADEOS_BACKEND_BLUEPRINT.md` §20, rows 2–3). |
| 2 | Configuration & Catalogs | Configuration (incl. Catalogs sub-module) | The most upstream business context (`TRADEOS_DOMAIN_MODEL.md` §4.3) — Evaluation cannot compute a Score, and Trading cannot validate a referenced Setup/Session/Strategy/Entry Trigger, without this existing and seeded first (`TRADEOS_BACKEND_BLUEPRINT.md` §20, rows 4–5). |
| 3 | Evaluation Engine | Evaluation (5 engines) | Trading's `RegisterTrade` Use Case requires a working Evaluation service in the same transaction (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03) — this must exist before Trading can be exercised end-to-end, not merely unit-tested in isolation (`TRADEOS_BACKEND_BLUEPRINT.md` §20, row 6). |
| 4 | Trading | Trading (Trades, Checklist, Mistake tagging) | Depends on Evaluation, Configuration, and Catalogs all being usable (`TRADEOS_BACKEND_BLUEPRINT.md` §20, row 7) — the busiest and most central module, and the first point at which the system produces a real, end-to-end scored Trade. |
| 5 | Journal & Mistakes | Journal, Mistakes | Both share the same "Estimated Implementation Order" position in `TRADEOS_BACKEND_BLUEPRINT.md` §20 (row 8) because both depend only on Trading already existing and are independently buildable in parallel once it does. |
| 6 | Analytics (Statistics) | Statistics | Needs real Trade + Evaluation data to aggregate meaningfully (`TRADEOS_BACKEND_BLUEPRINT.md` §20, row 9) — functionally buildable earlier, but validating it is unconvincing without Phase 4's data. |
| 7 | Playbook | Playbook | Its detail view composes Statistics' by-dimension output (`TRADEOS_DOMAIN_MODEL.md` §8.8) — the last of the confirmed Bounded Context modules for exactly this reason (`TRADEOS_BACKEND_BLUEPRINT.md` §20, row 10). |
| 8 | Dashboard | Dashboard (composition only) | Composes Trades + Statistics into one view (`TRADEOS_API_SPECIFICATION.md` §5.1) — cannot exist meaningfully before both of its sources do. |
| 9 | Deployment & Production Hardening | Cross-cutting | Hardens and ships what Phases 0–8 already built (`TRADEOS_SYSTEM_ARCHITECTURE.md` §12) — never a source of new business capability, so it is last by definition. |

**Modules explicitly excluded from this ordering:** Reports, AI Coaching, Notifications, Broker/Exchange Integration — none has a confirmed Domain Model entity, database table, or API endpoint (Section 4). They have no position in this order because they are not part of this plan.

---

## 7. Milestones

Each milestone is a demonstrable, testable state of the running system — not a document or a phase boundary in the abstract.

| ID | Milestone | Demonstrable When | Corresponds To |
|---|---|---|---|
| M1 | **Platform Foundation Live** | The backend boots as a modular monolith, a user can register/log in/refresh/log out, `platform.event_log` records a real event, and a liveness check responds — all behind TLS. | End of Phase 0 + Phase 1 |
| M2 | **Configuration Seeded** | A default `ScoringConfigurationVersion` is published; all five Catalog kinds (Setup, Session, Strategy, Entry Trigger, Mistake Tag) hold real, Excel-derived seed data (`PROJECT_AUDIT.md` Section 3.1). | End of Phase 2 |
| M3 | **Evaluation Engine Complete** | All five engines (Confidence, Quality, Execution, Market Context, Bias) compute scores against seeded Configuration; `POST /evaluation/preview` returns a fully explained score; the historical `round_half_up` regression test (`TRADEOS_BACKEND_BLUEPRINT.md` §15) passes. | End of Phase 3 |
| M4 | **First Real Trade, End to End** | A trader logs a Trade through the frontend (Simple or Pro), it is scored synchronously by all active engines, closed, re-evaluated once, and a Mistake is tagged to it — all without a silent failure. | End of Phase 4 |
| M5 | **Reflection & History Online** | Journal entries (trade-scoped and period-scoped) and the Mistake priority ranking both function against real Trade data. | End of Phase 5 |
| M6 | **Analytics Trustworthy** | Statistics Overview, By-Dimension, and Rolling tabs all return figures that are independently verifiable by hand-computing them from the same underlying Trades (Domain Invariant DI-11). | End of Phase 6 |
| M7 | **Playbook Live** | A Playbook Setup's detail view shows genuinely computed, non-stored performance data sourced from Statistics. | End of Phase 7 |
| M8 | **Full Navigable Application** | Every confirmed frontend module (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 3) is reachable from the sidebar, including a composed Dashboard as the landing page. | End of Phase 8 |
| M9 | **Production Deployment** | The containerized backend and the static frontend build both run on their target hosting platform, against a managed PostgreSQL instance, over TLS, with all Section 16 blocking Open Questions either resolved or explicitly, documentedly deferred. | End of Phase 9 |

---

## 8. Phases

Only phases with a confirmed Bounded Context, database schema, API module, and frontend module — or a cross-cutting concern explicitly named upstream — are included, per this document's own mandate (Section 4). This excludes Reports, AI, and Notifications from the example phase list in this document's own prompt; they appear only in Section 17.

### Phase 0 — Infrastructure & Platform
Cross-cutting foundation: modular monolith scaffolding (one top-level module folder per Bounded Context, `TRADEOS_BACKEND_BLUEPRINT.md` Section 16), the in-process Domain Event dispatcher (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 6.1), `platform.event_log` (`TRADEOS_DATABASE_DESIGN.md` Section 6.18), authentication middleware wiring (JWT verification at the Presentation boundary, `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-07), correlation-ID/logging middleware (`TRADEOS_BACKEND_BLUEPRINT.md` Section 11), and the frontend application shell (routing, API client layer, design system tokens, error-envelope handling, `TRADEOS_FRONTEND_BLUEPRINT.md` Sections 2.2, 2.8, 14).

### Phase 1 — Identity & Preferences (Authentication)
Backend: `UserAccount` registration/login/refresh/logout (`TRADEOS_DOMAIN_MODEL.md` Section 8.11; `TRADEOS_API_SPECIFICATION.md` Section 6.1), `UserPreferences` read/update (`TRADEOS_DOMAIN_MODEL.md` Section 8.12). Frontend: Login/Register pages, Settings — Preferences page (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 3).

### Phase 2 — Configuration & Catalogs
Backend: `ScoringCriterion`/`ScoringWeight`/`ScoringConfiguration` version lifecycle including publish (`TRADEOS_DOMAIN_MODEL.md` Sections 8.4–8.6; `TRADEOS_DATABASE_DESIGN.md` Section 7), and `Catalog`/`CatalogEntry` management for all five kinds (`TRADEOS_DOMAIN_MODEL.md` Section 8.7; `TRADEOS_DATABASE_DESIGN.md` Section 6.8) — one backend module per `TRADEOS_BACKEND_BLUEPRINT.md` Section 3.6, exposed as two API surfaces. Frontend: Configuration — Scoring Versions page, Catalogs Management page (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 5.5, 5.7).

### Phase 3 — Evaluation Engine
Backend: the `EvaluationEngine` domain service, all five engines (Confidence, Quality, Execution, Market Context, Bias), `POST /evaluation/preview` (`TRADEOS_DOMAIN_MODEL.md` Section 12.1; `TRADEOS_API_SPECIFICATION.md` Section 6.5). Frontend: the live Evaluation preview widget embedded in Trade Entry (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 6.3) — the full Rule Explorer *page* is deferred to Phase 4, since it explains a *historical* Trade's score and needs real Trades to explain (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 5.4).

### Phase 4 — Trading
Backend: `RegisterTrade`, `CloseTrade`, `ReevaluateTrade`, `AmendTrade`, `DeleteTrade` (soft), `TagMistake` (`TRADEOS_BACKEND_BLUEPRINT.md` Sections 4.1–4.3, 4.6, 4.8); `ChecklistSnapshot` capture; MFE/MAE/R-multiple/Captured %/Potential Left as computed, never-stored properties (`TRADEOS_DATABASE_DESIGN.md` Section 6.9). Frontend: Trades List, Trade Detail, Trade Entry (Simple and Pro), the Rule Explorer page, mistake-tagging UI (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 5.2–5.4, 6.2–6.7).

### Phase 5 — Journal & Mistakes
Backend: `CreateJournalEntry`/`UpdateJournalEntry`/`DeleteJournalEntry` (trade-scoped or period-scoped, never both, `TRADEOS_DOMAIN_MODEL.md` Section 8.10); `MistakePriorityRankingService`, read-only (`TRADEOS_DOMAIN_MODEL.md` Section 12.3). Frontend: Journal List/Detail, Mistakes Ranking page (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 5.7, 6.10–6.11).

### Phase 6 — Analytics (Statistics)
Backend: `StatisticsAggregationService` — Win Rate, Expectancy, Profit Factor, Average R, all-time and rolling, computed fresh on every call, never cached as a source of truth (`TRADEOS_DOMAIN_MODEL.md` Section 12.2; Domain Invariant DI-11). Frontend: Statistics page, three tabs (Overview / By Dimension / Rolling), mirroring the three confirmed endpoints exactly (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 4.2, 5.6).

### Phase 7 — Playbook
Backend: `PlaybookSetup` CRUD, attachments, and `PlaybookRecommendationService` output as a suggestion only (never an automatic edit, `TRADEOS_DOMAIN_MODEL.md` Section 12.4) — noting **Known Gap BE-4** (Section 15): this service has no confirmed endpoint yet. Frontend: Playbook List, Playbook Setup Detail (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 5.7).

### Phase 8 — Dashboard
Backend: `GET /dashboard`, a pure composition endpoint over already-built Trades and Statistics capability — introduces no new business logic or data (`TRADEOS_API_SPECIFICATION.md` Section 5.1). Frontend: the Dashboard page (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 5.1).

### Phase 9 — Deployment & Production Hardening
Containerize the backend as a single deployable (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1); provision a managed PostgreSQL instance; static-host the React/TypeScript frontend build independently of the backend (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8.5 clarifies this is a genuinely new build, not a continuation of the `TradeOS_UI_v3` prototype); enforce TLS end to end; wire secrets management for database credentials and signing keys (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1); resolve or explicitly defer every blocking Open Question in Section 16.

---

## 9. Sprint Breakdown

Each phase (Section 8) is broken into sprints. "Sprint" here is a sequencing/scoping unit, not a time-box (Section 4). Every sprint's Exit Criteria must be independently verifiable — a sprint is not "done" because code was written, but because its Exit Criteria hold.

### Phase 0 — Infrastructure & Platform

**Sprint 0.1 — Backend Skeleton & Event Infrastructure**
- *Objectives:* stand up the Modular Monolith's module-folder structure (`TRADEOS_BACKEND_BLUEPRINT.md` Section 16); implement the in-process Domain Event dispatcher and `platform.event_log` writer.
- *Deliverables:* an empty-but-structured backend repository with one folder per Bounded Context; a working event publish/subscribe path exercised by a trivial test event; the `platform` Postgres schema with `event_log` created.
- *Dependencies:* none — this is the entry point of the entire plan.
- *Exit Criteria:* a synthetic event published by a throwaway test handler is durably recorded in `platform.event_log` and visible via a direct query; module folders exist matching every Bounded Context named in `TRADEOS_DOMAIN_MODEL.md` Section 4.

**Sprint 0.2 — Auth Middleware & Correlation IDs**
- *Objectives:* wire JWT verification at the Presentation boundary (no domain module implements its own auth check, `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1); generate and thread a correlation ID through every request's logs.
- *Deliverables:* a request-scoped middleware stack; a rejected-request test proving an unauthenticated call to any protected route returns `401` before reaching a Use Case.
- *Dependencies:* Sprint 0.1.
- *Exit Criteria:* a request without a bearer token is rejected at the boundary layer, never inside a Use Case; every log line for one request shares one correlation ID.

**Sprint 0.3 — Frontend Application Shell**
- *Objectives:* routing skeleton, the API client layer (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 2.2), the standard error-envelope handling path (Section 2.8, Section 17), and design system tokens (dark theme only, Section 14).
- *Deliverables:* a runnable frontend shell with an empty route per confirmed frontend module (Section 3), a single shared error-banner component, no feature logic yet.
- *Dependencies:* none (parallelizable with Sprint 0.1–0.2).
- *Exit Criteria:* every confirmed frontend module has a routable, empty placeholder page; a simulated API error renders through the one shared error path, not a page-specific handler.

### Phase 1 — Identity & Preferences

**Sprint 1.1 — Identity Backend**
- *Objectives:* implement Register/Login/Refresh/Logout Use Cases (`TRADEOS_BACKEND_BLUEPRINT.md` Section 4.8); `identity.user_accounts` table (`TRADEOS_DATABASE_DESIGN.md` Section 6.1).
- *Deliverables:* all four Identity endpoints functioning per `TRADEOS_API_SPECIFICATION.md` Section 6.1, including refresh-token rotation (Section 4.3).
- *Dependencies:* Phase 0 complete.
- *Exit Criteria:* a client can register, log in, use an access token, refresh it, and log out (revoking the refresh token) — all against real persistence, with password hashes never in plaintext (`TRADEOS_DATABASE_DESIGN.md` Section 11.1).

**Sprint 1.2 — Preferences Backend + Frontend, and Auth Frontend**
- *Objectives:* `UserPreferences` GET/PATCH (auto-created with defaults at registration, `TRADEOS_API_SPECIFICATION.md` Section 6.3); Login/Register pages; Settings — Preferences page.
- *Deliverables:* a first fully vertical (frontend-to-database) slice of the application — a user can register and log in through the UI, and change their theme/language.
- *Dependencies:* Sprint 1.1; Sprint 0.3.
- *Exit Criteria:* Milestone M1 is achieved (Section 7).

### Phase 2 — Configuration & Catalogs

**Sprint 2.1 — Configuration Backend**
- *Objectives:* `ScoringCriterion`, `ScoringWeight`, `ScoringConfigurationVersion` CRUD plus `PublishScoringConfigurationVersion` (`TRADEOS_BACKEND_BLUEPRINT.md` Section 4.4); seed the first published version from the Excel-derived criteria/weights already confirmed in `PROJECT_AUDIT.md` Section 3.1/6.
- *Deliverables:* one published `ScoringConfigurationVersion` covering all five engines' criteria and weights, per `TRADEOS_DATABASE_DESIGN.md` Section 7.
- *Dependencies:* Phase 1 (a `user_id` must exist to attribute the seed action).
- *Exit Criteria:* exactly one `ScoringConfigurationVersion` has `status = published`; publishing a second draft correctly supersedes it (Domain Invariant DI-06/DI-07 enforced, verified by a specific test).

**Sprint 2.2 — Catalogs Backend**
- *Objectives:* `CatalogEntry` CRUD and deactivation for all five kinds (`TRADEOS_BACKEND_BLUEPRINT.md` Section 4.8); seed with the real Setups/Sessions/Strategies/Entry Triggers/Mistake Tags already confirmed to exist from prior design work (`PROJECT_AUDIT.md` Section 3.1).
- *Deliverables:* all five catalog kinds populated with real entries; deactivation tested to confirm existing Trade references (once Phase 4 exists) would remain valid.
- *Dependencies:* Sprint 2.1 (same module family, `TRADEOS_BACKEND_BLUEPRINT.md` Section 3.6).
- *Exit Criteria:* the `(kind, name)` uniqueness constraint is verified (`TRADEOS_DATABASE_DESIGN.md` Section 6.8); every seeded entry is active by default.

**Sprint 2.3 — Configuration & Catalogs Frontend**
- *Objectives:* Configuration — Scoring Versions page (view/publish); Catalogs Management page (CRUD + deactivate).
- *Deliverables:* an admin-facing screen pair fully wired to Sprints 2.1–2.2's endpoints.
- *Dependencies:* Sprints 2.1–2.2; Sprint 0.3.
- *Exit Criteria:* Milestone M2 is achieved (Section 7).

### Phase 3 — Evaluation Engine

**Sprint 3.1 — Confidence & Quality Engines**
- *Objectives:* implement/port the `EvaluationEngine` domain service and wire the Confidence and Quality engines against seeded Configuration (`TRADEOS_DOMAIN_MODEL.md` Section 12.1) — Confidence already has reference code (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 15's Known Gap); Quality is net-new against the same generic pattern.
- *Deliverables:* both engines produce correct scores/grades against known test cases; the historical `round_half_up` rounding defect (`TRADEOS_BACKEND_BLUEPRINT.md` Section 15) has a permanent regression test.
- *Dependencies:* Phase 2 complete.
- *Exit Criteria:* Domain Invariant DI-03 (Quality independent of P&L) is enforced and tested; both engines are unit-tested with zero infrastructure dependencies (`TRADEOS_BACKEND_BLUEPRINT.md` Section 15).

**Sprint 3.2 — Execution, Market Context & Bias Engines**
- *Objectives:* implement the remaining three engines, including Bias's signed normalization (the only engine using it, Domain Invariant DI-05) and Market Context's independence from Bias's direction (DI-04).
- *Deliverables:* all five engines complete; `POST /evaluation/preview` functional end-to-end.
- *Dependencies:* Sprint 3.1.
- *Exit Criteria:* Domain Invariants DI-04 and DI-05 are each enforced and tested; a preview call against a full set of checklist answers returns all five scores/grades with a complete per-criterion breakdown (Domain Invariant DI-08).

**Sprint 3.3 — Evaluation Preview Frontend**
- *Objectives:* the live-updating Evaluation preview widget embedded in the (not-yet-built) Trade Entry flow's design, buildable now against `POST /evaluation/preview` alone.
- *Deliverables:* a standalone, testable preview component.
- *Dependencies:* Sprint 3.2; Sprint 0.3.
- *Exit Criteria:* Milestone M3 is achieved (Section 7).

### Phase 4 — Trading

**Sprint 4.1 — Core Trade Registration**
- *Objectives:* `RegisterTrade` (`TRADEOS_BACKEND_BLUEPRINT.md` Section 4.1) — the single most important write in the system; `ChecklistSnapshot` capture; synchronous, same-transaction Evaluation call.
- *Deliverables:* `POST /trades` fully functional, including Idempotency-Key handling (`TRADEOS_API_SPECIFICATION.md` Section 3.6) and computed properties (`r_multiple`, MFE/MAE in R, Captured %, Potential Left) returned but never stored.
- *Dependencies:* Phase 3 complete.
- *Exit Criteria:* a registered Trade has exactly one current `EvaluationSnapshot`; Domain Invariants INV-TRADE-01/02 are enforced and tested; a duplicate `Idempotency-Key` never double-creates a Trade.

**Sprint 4.2 — Amend, Close, Re-evaluate, Delete**
- *Objectives:* `AmendTrade`, `CloseTrade`, `ReevaluateTrade`, `DeleteTrade` (soft) (`TRADEOS_BACKEND_BLUEPRINT.md` Sections 4.2–4.3, 4.8).
- *Deliverables:* the full Trade lifecycle (`TRADEOS_DOMAIN_MODEL.md` Section 13.1) operable via the API.
- *Dependencies:* Sprint 4.1.
- *Exit Criteria:* re-evaluating a Trade produces a *new* `EvaluationSnapshot` and correctly flips the prior one's `is_current` flag, both retained forever (Domain Invariant DI-06); a soft-deleted Trade's snapshots remain intact and orphaned, never deleted (`TRADEOS_DATABASE_DESIGN.md` Section 2.6).

**Sprint 4.3 — Mistake Tagging**
- *Objectives:* `TagMistake` (`TRADEOS_BACKEND_BLUEPRINT.md` Section 4.6).
- *Deliverables:* `trade_mistakes` junction writes, validated against `kind=mistake_tag` and active status.
- *Dependencies:* Sprint 4.1; Phase 2 (Catalogs).
- *Exit Criteria:* tagging an inactive or wrong-kind catalog entry is rejected with `422`.

**Sprint 4.4 — Trading Frontend**
- *Objectives:* Trades List, Trade Detail, Trade Entry (Simple and Pro paths, `TRADEOS_FRONTEND_BLUEPRINT.md` Section 6.2–6.3), the Rule Explorer page (Section 6.5), mistake-tagging UI (Section 6.7).
- *Deliverables:* a trader can, entirely through the UI, log a Trade, watch its live Evaluation preview, save it, close it, re-evaluate it, tag a Mistake, and open the Rule Explorer to see the full scoring breakdown.
- *Dependencies:* Sprints 4.1–4.3; Sprint 3.3.
- *Exit Criteria:* Milestone M4 is achieved (Section 7).

### Phase 5 — Journal & Mistakes

**Sprint 5.1 — Journal Backend + Frontend**
- *Objectives:* `CreateJournalEntry`/`UpdateJournalEntry`/`DeleteJournalEntry`; Journal List/Detail pages.
- *Deliverables:* trade-scoped and period-scoped entries both functional; the exactly-one-reference check constraint verified (`TRADEOS_DATABASE_DESIGN.md` Section 6.17).
- *Dependencies:* Phase 4 (for trade-scoped entries only — period-scoped entries need no Trade to exist first, `TRADEOS_BACKEND_BLUEPRINT.md` Section 20, row 8).
- *Exit Criteria:* creating an entry with both or neither reference type is rejected with `422`.

**Sprint 5.2 — Mistakes Ranking Backend + Frontend**
- *Objectives:* `MistakePriorityRankingService`; Mistakes Ranking page.
- *Deliverables:* a read-only ranking of tagged Mistakes by frequency, cost, and priority, computed on demand (no persistence, `TRADEOS_BACKEND_BLUEPRINT.md` Section 3.8).
- *Dependencies:* Phase 4 (Mistake tagging must have real data to rank); Phase 2 (Catalogs, for tag metadata).
- *Exit Criteria:* Milestone M5 is achieved (Section 7).

### Phase 6 — Analytics (Statistics)

**Sprint 6.1 — Statistics Overview & By-Dimension**
- *Objectives:* `StatisticsAggregationService`'s all-time computation, grouped by Strategy/Setup/Session/Direction (`TRADEOS_DOMAIN_MODEL.md` Section 12.2).
- *Deliverables:* `GET /statistics/overview` and `GET /statistics/by-dimension` functional against real Trade + Evaluation data from Phase 4.
- *Dependencies:* Phase 4 complete (data), Phase 3 complete (Evaluation scores to aggregate).
- *Exit Criteria:* a hand-computed Win Rate/Expectancy over the same Trade set matches the endpoint's output exactly (Domain Invariant DI-11 — reproducibility, not caching).

**Sprint 6.2 — Rolling Statistics + Frontend**
- *Objectives:* the configurable moving-window comparison (`TRADEOS_DOMAIN_MODEL.md` Section 2.3); Statistics page, all three tabs.
- *Deliverables:* `GET /statistics/rolling`; the full Statistics page wired to all three endpoints.
- *Dependencies:* Sprint 6.1.
- *Exit Criteria:* Milestone M6 is achieved (Section 7).

### Phase 7 — Playbook

**Sprint 7.1 — Playbook Backend**
- *Objectives:* `PlaybookSetup` CRUD, attachments, 1:1 linkage to a `kind=setup` Catalog entry (`TRADEOS_DATABASE_DESIGN.md` Section 6.15).
- *Deliverables:* Playbook definitions manageable via the API; performance data explicitly never stored on the setup itself, always a live Statistics read.
- *Dependencies:* Phase 2 (Catalogs), Phase 6 (Statistics).
- *Exit Criteria:* a Playbook Setup's performance figures match the equivalent Statistics by-dimension query for that same Setup, exactly.

**Sprint 7.2 — Playbook Frontend**
- *Objectives:* Playbook List, Playbook Setup Detail pages.
- *Deliverables:* a trader can view and edit setup documentation alongside genuinely live performance data.
- *Dependencies:* Sprint 7.1.
- *Exit Criteria:* Milestone M7 is achieved (Section 7).

### Phase 8 — Dashboard

**Sprint 8.1 — Dashboard Composition**
- *Objectives:* `GET /dashboard`, composing already-built Trades + Statistics capability; the Dashboard page.
- *Deliverables:* one screen giving at-a-glance operational awareness (`TRADEOS_PRODUCT_BIBLE.md` Section 9), introducing no new backend logic.
- *Dependencies:* Phases 4 and 6 complete.
- *Exit Criteria:* Milestone M8 is achieved (Section 7).

### Phase 9 — Deployment & Production Hardening

**Sprint 9.1 — Containerization & Managed Database**
- *Objectives:* containerize the backend as one deployable (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1); provision a managed PostgreSQL instance; apply all migrations from Phases 0–8 in order.
- *Deliverables:* a backend container image; a live managed database with the full schema.
- *Dependencies:* Phases 0–8 complete.
- *Exit Criteria:* the containerized backend passes the same integration test suite used in every prior phase, against the managed database.

**Sprint 9.2 — Frontend Static Hosting & TLS**
- *Objectives:* build and statically host the React/TypeScript frontend independently of the backend (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12.1, Section 8.5); enforce TLS end to end.
- *Deliverables:* a publicly reachable, TLS-terminated frontend build calling the deployed backend's `/api/v1` surface.
- *Dependencies:* Sprint 9.1.
- *Exit Criteria:* the deployed frontend completes the same Milestone M4 walkthrough (register → log a Trade → close it → view Statistics) against production infrastructure.

**Sprint 9.3 — Hardening & Blocking-Question Resolution**
- *Objectives:* secrets management for database credentials and signing keys (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1); resolve or explicitly, documentedly defer every Section 16 blocking Open Question.
- *Deliverables:* no secret committed to source control; a written resolution (or explicit deferral with owner and rationale) for each Section 16 item.
- *Dependencies:* Sprints 9.1–9.2.
- *Exit Criteria:* Milestone M9 is achieved (Section 7).

---

## 10. Testing Strategy

Grounded directly in `TRADEOS_BACKEND_BLUEPRINT.md` Section 15's Testing Blueprint and `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9's Correctness-first priority ordering — this section applies that same standing philosophy per phase rather than restating it once and leaving each phase to interpret it independently.

| Phase | Unit Tests | Integration Tests | End-to-End Tests | Regression Tests |
|---|---|---|---|---|
| 0 — Infrastructure | Event dispatcher's publish/subscribe logic in isolation | Middleware stack (auth + correlation ID) against a real request pipeline | A full unauthenticated-request rejection round trip | None yet — nothing to regress |
| 1 — Identity & Preferences | Password hashing, token claim construction | Register→Login→Refresh→Logout against real persistence (`identity` schema) | UI walkthrough: register, log in, change a preference | Refresh-token rotation reuse is rejected (single-use, Section 4.3) |
| 2 — Configuration & Catalogs | Weight/criterion validation rules (`max_value >= min_value`) | Publish action's atomic two-row status flip (draft→published, prior→superseded) | UI walkthrough: view, publish a Configuration version, deactivate a Catalog entry | The `(kind, name)` uniqueness defect class from `PROJECT_AUDIT.md` (category name drift) |
| 3 — Evaluation | Each of the 5 engines against known-input/known-output cases; signed vs. unsigned normalization (DI-05) | `EvaluationEngine` against a real Configuration read from the database | Preview call through the UI reflecting checklist input changes live | The `round_half_up` rounding defect (`TRADEOS_BACKEND_BLUEPRINT.md` §15) |
| 4 — Trading | INV-TRADE-01/02 validation logic; computed-property math (R-multiple, MFE/MAE, Captured %, Potential Left) | `RegisterTrade` full transaction (Trade + Checklist + Evaluation Snapshot + events, one commit) | UI walkthrough: log, close, re-evaluate, tag a Mistake on a real Trade | Idempotency-Key replay never double-creates a Trade; re-evaluation never leaves two "current" snapshots |
| 5 — Journal & Mistakes | Exactly-one-reference validation | Journal entry creation against real `trades` foreign key | UI walkthrough: write a trade-scoped and a period-scoped entry | The Mistake ranking excludes deactivated tags' *new* use while still counting their historical occurrences |
| 6 — Analytics | Win Rate/Expectancy/Profit Factor formulas against hand-computed fixtures | Statistics endpoints against a real, seeded Trade set | UI walkthrough: all three Statistics tabs against the same data | Statistics output never silently drifts from a direct recomputation (Domain Invariant DI-11) |
| 7 — Playbook | 1:1 Setup-to-Catalog-entry linkage validation | Playbook detail composing a real Statistics by-dimension call | UI walkthrough: edit a Setup's definition, observe unchanged live performance | Playbook never stores a performance number that could go stale |
| 8 — Dashboard | None of its own (pure composition, no new logic) | The composition call against real Trades + Statistics | UI walkthrough: Dashboard as landing page after login | Dashboard never duplicates a number differently than its source endpoint returns it |
| 9 — Deployment | N/A | Full backend integration suite re-run against the containerized build + managed database | The Milestone M4 walkthrough re-run against production infrastructure | Every regression test from Phases 0–8 re-run once, post-deployment, before M9 is declared met |

**Cross-cutting rule, every phase:** every Domain Invariant touched by that phase's Use Cases has at least one test asserting it is enforced (`TRADEOS_BACKEND_BLUEPRINT.md` Section 15) — a phase is not exit-eligible with an untested invariant it introduced.

---

## 11. Definition of Done

### 11.1 General Definition of Done (applies to every phase)

A phase is Done only when **all** of the following hold — this is the baseline every phase-specific Exit Criteria (Section 9) adds to, never substitutes for:

1. Every endpoint the phase introduces matches its documented contract in `TRADEOS_API_SPECIFICATION.md` Section 6 exactly (verified by a contract test, `TRADEOS_BACKEND_BLUEPRINT.md` Section 15).
2. Every Domain Invariant the phase's Use Cases touch has a passing, named test (Section 10).
3. Every database migration the phase requires is forward-only and additive unless explicitly following the expand/contract process (`TRADEOS_DATABASE_DESIGN.md` Section 13.3).
4. No Use Case in the phase fails silently — every failure path returns the standard error envelope (`TRADEOS_API_SPECIFICATION.md` Section 8) and is logged with a correlation ID (`TRADEOS_BACKEND_BLUEPRINT.md` Section 11).
5. Every frontend page the phase introduces has a defined Loading state and, where list-shaped, a defined Empty state (`TRADEOS_FRONTEND_BLUEPRINT.md` Sections 2.9–2.10).
6. Every Domain Event the phase's Use Cases publish is durably recorded in `platform.event_log` (`TRADEOS_DATABASE_DESIGN.md` Section 6.18).
7. The phase's row in the Traceability Matrix (Section 14) is confirmed accurate — no capability was built that doesn't trace back to one of the eight frozen documents.
8. Any new Known Gap or Open Question discovered during the phase is registered (Sections 15–16), never silently patched.

### 11.2 Milestone-Level Definition of Done

A Milestone (Section 7) is Done only when every phase feeding into it meets Section 11.1, **and** the milestone's own "Demonstrable When" condition (Section 7's table) is independently verified — not inferred from its component phases being individually done.

---

## 12. Risk Register

Every risk below is grounded in a concern already identified in one of the eight frozen documents — none is invented for this document (per its own mandate, Section 4).

| ID | Risk | Grounded In | Mitigation |
|---|---|---|---|
| R-1 | Silent correctness failures in the Evaluation Engine, the exact defect class that cost the most during the Excel's own construction | `PROJECT_AUDIT.md` Section 3.4; `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9 (Correctness ranked #1) | Phase 3's near-exhaustive unit test coverage and named regression tests (Section 10); Architectural Principle 5 (fail loudly, never silently) |
| R-2 | Underestimating Phase 9's frontend effort by treating it as a "continuation" of `TradeOS_UI_v3` rather than a genuine rewrite onto React + TypeScript | `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8.5 (the documentation correction recorded 2026-07-25) | Sprint 9.2 scoped explicitly as a new build; no sprint in this plan assumes reusable `TradeOS_UI_v3` code, only its validated UX/IA |
| R-3 | Concurrent edits to the same aggregate (multi-tab or, later, multi-user) with no defined isolation/conflict strategy | `TRADEOS_BACKEND_BLUEPRINT.md` Open Questions BE-5, BE-6 | Deferred by design at current single-user scale (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2); flagged here so it is revisited immediately if Product Bible Open Question 2 resolves toward multi-user |
| R-4 | A trader's expectation that publishing a new Configuration version "recalculates" historical Trades, when only a per-Trade re-evaluation action actually exists | `TRADEOS_BACKEND_BLUEPRINT.md` Open Question BE-10 (rated Medium-High) | Phase 2/4 UI copy must be explicit that publishing does not retroactively rescore existing Trades; bulk re-evaluation remains a Future Enhancement (Section 17), not silently assumed as already covered |
| R-5 | Deploying (Phase 9) without a defined health-check endpoint contract, since none exists in `TRADEOS_API_SPECIFICATION.md` | `TRADEOS_BACKEND_BLUEPRINT.md` Open Question BE-7 | Registered as a genuinely blocking Open Question (Section 16, OQ-1) — must be resolved (an API Specification amendment) before Sprint 9.1 is considered complete |
| R-6 | Building Trading (Phase 4) against `Mistakes` as free text instead of the target catalog-based model, re-introducing the exact class of drift `PROJECT_AUDIT.md` found in the Excel | `TRADEOS_DOMAIN_MODEL.md` KDD-06; `TRADEOS_DATABASE_DESIGN.md` Section 3.1 (already resolved at the schema level as `configuration.catalog_entries`, kind=mistake_tag) | Sprint 4.3 implements Mistake tagging exclusively against the catalog-based model already frozen in the Database Design — the free-text legacy approach is not carried forward |
| R-7 | Scope ambiguity in Phase 4/9 over whether historical Excel data (`Trading_Journal_v2_0_Stable.xlsx`) is migrated into the application | `TRADEOS_PRODUCT_BIBLE.md` Open Question 5 | Registered as a blocking Open Question (Section 16, OQ-3) — must be resolved before Phase 4's scope (whether a one-time import sprint is needed) is finalized |
| R-8 | Deploying (Phase 9) with an undefined encryption-at-rest posture | `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.2; `TRADEOS_PRODUCT_BIBLE.md` Open Question 3 | Registered as a blocking Open Question (Section 16, OQ-4) for Sprint 9.3 specifically |
| R-9 | Analytics (Phase 6) becoming slow at real trade volume, since it is deliberately computed on demand rather than cached | `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04; `TRADEOS_DATABASE_DESIGN.md` Section 10.6 | Explicitly deferred per Architectural Principle 4 — not solved speculatively in this plan; indexing already provisioned (`TRADEOS_DATABASE_DESIGN.md` Section 10.1) is the first lever if it is ever demonstrated necessary |

---

## 13. Implementation Readiness Matrix

This consolidates `TRADEOS_BACKEND_BLUEPRINT.md` Section 20's backend-only readiness assessment with the corresponding Frontend, API, and Database columns each module already has in its own upstream document's traceability matrix (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 19; `TRADEOS_API_SPECIFICATION.md` Section 19; `TRADEOS_DATABASE_DESIGN.md` Section 15).

| Module | Status | Blocking Dependencies | Documents Required | API Required | Database Required | Frontend Required | Backend Required |
|---|---|---|---|---|---|---|---|
| Infrastructure / Platform | **Ready** | None | System Architecture §2–3, 6; Database Design §6.18 | N/A (cross-cutting) | `platform` schema | App shell (routing, API client, error handling) | Event dispatcher, auth middleware, correlation IDs |
| Identity | **Ready** | Infrastructure | Domain Model §8.11; Database Design §6.1; API Spec §6.1–6.2 | Authentication, Users | `identity` schema | Login, Register pages | Register/Login/Refresh/Logout Use Cases |
| Preferences | **Ready** | Identity | Domain Model §8.12; Database Design §6.2; API Spec §6.3 | Preferences | `preferences` schema | Settings — Preferences page | UpdatePreferences Use Case |
| Configuration | **Partial** | Infrastructure | Domain Model §8.4–8.6; Database Design §6.3–6.7, §7; API Spec §6.6 | Configuration | `configuration` schema | Scoring Versions page | Criterion/Weight/Version Use Cases incl. publish |
| Catalogs | **Partial** | Configuration | Same as Configuration + Database Design §6.8 | Catalogs | `configuration.catalog_entries` | Catalogs Management page | CatalogEntry CRUD + deactivate Use Cases |
| Evaluation | **Partial** (Confidence only wired today) | Configuration | Domain Model §8.2, 12.1; Database Design §7; API Spec §6.5 | Evaluation | None (pure domain service) | Live preview widget | 5-engine `EvaluationEngine` domain service |
| Trading | **Partial** (basic CRUD exists) | Evaluation, Configuration, Catalogs | Domain Model §8.1, 8.3; Database Design §6.9–6.14; API Spec §6.4 | Trades | `trading` schema | Trades List/Detail/Entry, Rule Explorer | Register/Close/Reevaluate/Amend/Delete/TagMistake Use Cases |
| Journal | **Planned** | Trading (trade-scoped only) | Domain Model §8.10; Database Design §6.17; API Spec §6.11 | Journal | `journal` schema | Journal List/Detail | Create/Update/Delete Use Cases |
| Mistakes | **Planned** | Trading, Catalogs | Domain Model §12.3; API Spec §6.9 | Mistakes | None (pure read) | Mistakes Ranking page | `MistakePriorityRankingService` |
| Statistics | **Planned** | Trading, Evaluation | Domain Model §12.2; API Spec §6.10 | Statistics | None (pure read) | Statistics page (3 tabs) | `StatisticsAggregationService` |
| Playbook | **Planned** | Catalogs, Statistics | Domain Model §8.8; Database Design §6.15–6.16; API Spec §6.8 | Playbook | `playbook` schema | Playbook List/Detail | PlaybookSetup CRUD + `PlaybookRecommendationService` |
| Dashboard | **Planned** | Trading, Statistics | API Spec §5.1 | Dashboard (composition) | None (composition) | Dashboard page | Single composition endpoint |
| Deployment | **Not started** | All modules above | System Architecture §8, 11–12 | N/A | Managed instance provisioning | Static build hosting | Containerization |
| Reports, AI, Notifications, Broker Integration | **Blocked / Reserved** | No confirmed Domain Model entity | None can be written yet | Not designed | Not designed | Not designed | Not designed |

---

## 14. Traceability Matrix

Every phase must reference the canonical documents that justify it — no phase exists that cannot be traced back to all eight frozen documents at the level relevant to it.

| Phase | Product Bible | Domain Model | System Architecture | Database Design | API Specification | Frontend Blueprint | Backend Blueprint |
|---|---|---|---|---|---|---|---|
| 0 — Infrastructure | §4.2 (single user) | §4 (Bounded Contexts) | §2, 3, 6, 11 | §6.18 | N/A | §2.1–2.2, 2.8, 14 | §2, 3.12, 8, 11, 13, 16 |
| 1 — Identity & Preferences | §4.2 | §8.11–8.12 | ADR-07 | §6.1–6.2 | §6.1–6.3 | §3, §5.7 | §3.1–3.2, 4.8 |
| 2 — Configuration & Catalogs | §8, §9 | §4.3, 8.4–8.7 | — | §6.3–6.8, §7 | §6.6 | §5.5, §5.7 | §3.5–3.6, 4.4, 4.8 |
| 3 — Evaluation | §8 (entire) | §8.2, 12.1 | ADR-03 | §7 | §6.5 | §5.4, §6.3 | §3.4, 4.5, 5.1 |
| 4 — Trading | §9 (Trades module) | §8.1, 8.3, 13.1 | §4 | §6.9–6.14 | §6.4 | §5.2–5.4, §6.2–6.7 | §3.3, 4.1–4.3, 4.6, 4.8 |
| 5 — Journal & Mistakes | §9 | §8.10, 12.3 | — | §6.17 | §6.9, 6.11 | §5.7, §6.10–6.11 | §3.8, 3.10, 4.7, 4.8 |
| 6 — Analytics | §9, §13 | §12.2 | ADR-04 | §10.1, 10.6 | §6.10 | §4.2, §5.6 | §3.9, 4.8 |
| 7 — Playbook | §9 | §8.8, 12.4 | — | §6.15–6.16 | §6.8 | §5.7 | §3.7, 4.8 |
| 8 — Dashboard | §9 | — | — | — | §5.1 | §5.1 | — |
| 9 — Deployment | §10.3–10.4 | §17 (Future Reserved Domains, explicitly excluded) | §8, 11, 12 | §11, §13 | §14 (deferred) | — | §13, 21 (BE-7) |

---

## 15. Known Gaps

Carried forward from the eight frozen documents — this document resolves none of them, only maps them to the phase(s) they affect.

| ID (Source) | Topic | Affects Phase(s) |
|---|---|---|
| DB-1 (Database Design) | "Calendar" module — no Domain Model entity | None planned — not in scope (Section 4) |
| DB-2 (Database Design) | Mistake tagging after Trade closure — not blocked at the DB level | Phase 4 (Sprint 4.3) — application-layer decision, not a schema one |
| DB-3 / API-2 (Database Design / API Spec) | "Risk Profiles" / risk-limit validation — no Domain Model entity | None planned — no Trading endpoint depends on this today |
| DB-4 (Database Design) | No full point-in-time reconstruction of a Trade's past state, only that an amendment occurred | Phase 4 (Sprint 4.2) — accepted as-is per Database Design Section 9 |
| DB-5 (Database Design) | Plugin System / Marketplace — no entity anywhere | None planned |
| API-1 / FE-2 (API Spec / Frontend Blueprint) | Free-text search unimplemented | No phase includes a search UI (Section 4.6 of the Frontend Blueprint already forbids one until this resolves) |
| API-3 (API Specification) | Deprecation overlap period length unspecified | Phase 9 — irrelevant until a second API client exists |
| API-4 (API Specification) | "Trading Accounts" module — no entity | None planned |
| API-5 (API Specification) | Same as DB-1 | None planned |
| API-6 (API Specification) | Reports/Notifications — reserved namespace only | Excluded entirely (Section 4, Section 17) |
| FE-1 (Frontend Blueprint) | Offline behavior not designed | Phase 9 — minimal "offline" state only, no sync strategy |
| FE-3 (Frontend Blueprint) | Trade Detail as page vs. drawer | Phase 4 — resolved in favor of a full page per the Frontend Blueprint's own decision |
| FE-4 (Frontend Blueprint) | Autosave strategy unspecified for any form | Phase 4 (Trade Entry), Phase 2 (Configuration forms), Phase 5 (Journal) |
| FE-5 (Frontend Blueprint) | UI-level undo strategy unspecified | Phase 4, 5, 7 (any soft-deletable resource) |
| FE-6 (Frontend Blueprint) | Export capability not implemented | None planned — depends on the unconfirmed Reports module |
| FE-7 (Frontend Blueprint) | Equity curve — direction confirmed (backend must compute it), endpoint not yet specified | Phase 6 — cannot be built until `TRADEOS_API_SPECIFICATION.md` is amended with a supporting endpoint |
| FE-8 / FE-9 (Frontend Blueprint) | Unconfirmed modules; prior prototype modules not carried forward | None planned |
| BE-1, BE-2, BE-3 (Backend Blueprint) | Missing Domain Events for Identity actions, Trade deletion, and fine-grained Configuration edits | Phases 1, 4, 2 respectively — accepted as-is; `platform.event_log`'s timestamps provide partial audit coverage already |
| BE-4 (Backend Blueprint) | `PlaybookRecommendationService` has no confirmed endpoint | Phase 7 — the service can be implemented, but its output cannot be surfaced to the frontend until `TRADEOS_API_SPECIFICATION.md` is amended |
| BE-5, BE-6 (Backend Blueprint) | Concurrency/isolation strategy unspecified | See Risk R-3 (Section 12) |
| BE-9 (Backend Blueprint) | Background job technology unchosen | Deferred entirely — no phase in this plan requires one (Section 4) |
| BE-10 (Backend Blueprint) | Bulk re-evaluation of historical Trades never actually designed, only per-Trade | See Risk R-4 (Section 12); explicitly a Future Enhancement (Section 17), not part of Phase 4 |

---

## 16. Open Questions

Filtered strictly to items that genuinely block a phase's execution or its Definition of Done — the much larger set of non-blocking open items above (Section 15) is carried forward for visibility but does not stop implementation.

| ID | Question | Blocks | Why It Genuinely Blocks (Not Merely Informs) |
|---|---|---|---|
| OQ-1 | What is the health-check endpoint's contract (`BE-7`)? No frozen document names one. | Phase 9, Sprint 9.1's Exit Criteria | A managed hosting platform's load balancer/readiness probe needs a defined endpoint to call — Sprint 9.1 cannot be verified done without one, and this document cannot invent an endpoint on its own authority (Section 4) |
| OQ-3 | Does historical Excel data (`Trading_Journal_v2_0_Stable.xlsx`) migrate into the application, or does the Excel remain a permanent separate record (`TRADEOS_PRODUCT_BIBLE.md` Open Question 5)? | Phase 4's final scope | Determines whether a one-time data-import sprint must be added to Phase 4 — without an answer, Phase 4 cannot be declared complete with confidence that no further sprint is needed |
| OQ-4 | What is the encryption-at-rest standard (`TRADEOS_SYSTEM_ARCHITECTURE.md` Open Question 3 / Section 11.2)? | Phase 9, Sprint 9.3's Exit Criteria | Sprint 9.3 explicitly requires resolving or documented-deferring every blocking question before Milestone M9 — this is the one security item with a concrete Phase 9 action item (choose and apply a standard, or formally defer with a written rationale) |

**Explicitly not included here, and why:** Product Bible Open Questions 1 (academic vs. personal project), 2 (business model), and 6 (Mistakes free-text vs. catalog) are not listed because none blocks a phase in this plan — Question 1 affects ambition, not what v1 builds; Question 2 is architecturally deferred everywhere already (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-01, ADR-07); Question 6 is already resolved at the design level (the catalog-based model is canonical per `TRADEOS_DOMAIN_MODEL.md` KDD-06 and implemented as such in `TRADEOS_DATABASE_DESIGN.md` — see Risk R-6, Section 12). **Former OQ-2** (Product Bible Open Question 4 — Simple vs. Pro Trade Entry default) is likewise resolved as of Sprint 4.4: **Simple is the default daily workflow**; Pro remains first-class but secondary in visual hierarchy ("Simple (predeterminado)" / "Cambiar a Pro"). Both modes submit through the exact same `POST /trades` contract and share one domain model — only the capture experience differs (`TRADEOS_FRONTEND_BLUEPRINT.md` §5.7, §10; Principle 7).

---

## 17. Future Enhancements

Explicitly separated from this v1 implementation plan. None of the following has a phase, sprint, or milestone above — they are named here only so a future contributor extends this plan rather than mistaking one of these for something already scheduled.

- **Reports module** — reserved namespace only (`TRADEOS_API_SPECIFICATION.md` API-6; `TRADEOS_BACKEND_BLUEPRINT.md` §3.11); requires upstream Domain Model/API work before any phase can be written.
- **AI Coaching Layer** — a downstream, event-driven consumer of `TradeEvaluated`/`TradeClosed` (`TRADEOS_DOMAIN_MODEL.md` §17, §12.3 of the Product Bible); explicitly conditional on the Intelligence/Pattern Discovery layer existing first.
- **Notifications** — reserved (`TRADEOS_DOMAIN_MODEL.md` §17); no entity currently triggers one.
- **Broker/Exchange Integration & TradingView Synchronization** — upstream of Trading, supplying `RegisterTrade` calls automatically (`TRADEOS_SYSTEM_ARCHITECTURE.md` §13); would plug into Phase 4's existing Use Case without reopening it.
- **Bulk re-evaluation of historical Trades** — the capability Open Question BE-10 (Section 15) identifies as never actually designed beyond the per-Trade action already in Phase 4.
- **Intelligence / Pattern Discovery Layer** — a bounded, two-variable extension of Statistics (`TRADEOS_PRODUCT_BIBLE.md` §12.2); explicitly a precondition for AI Coaching.
- **Multi-Account / Team Workspaces** — conditional on Product Bible Open Question 2; would extend every phase's `user_id` scoping to a `workspace_id`, per `TRADEOS_DATABASE_DESIGN.md` §12, without redesigning any table built in Phases 0–9.
- **Mobile Application** — consumes the same `v1` API unchanged (`TRADEOS_API_SPECIFICATION.md` §17); no phase above assumes it does not exist, none builds it.
- **Plugin System / Marketplace** — no corresponding entity anywhere in the eight frozen documents; the least-defined future item of all.

---

## 18. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-25 | Initial Implementation Master Plan. Established the full dependency graph, a ten-phase implementation order (Infrastructure through Deployment), nine milestones, sprint-level breakdowns with objectives/deliverables/dependencies/exit criteria for every phase, a per-phase testing strategy, a general and milestone-level Definition of Done, a nine-item risk register grounded entirely in prior documented concerns, a consolidated frontend+backend+API+database readiness matrix, a full traceability matrix, a Known Gaps carry-forward table mapping every prior open item to the phase(s) it affects, four genuinely implementation-blocking Open Questions (filtered from a much larger non-blocking set), and an explicit Future Enhancements boundary excluding Reports, AI, Notifications, and Broker Integration from v1 scope entirely. |

**Status:** FROZEN. This is the ninth document of TradeOS. It contains no unresolved design decision of its own — only a sequencing of decisions already made in the eight documents before it, plus a filtered, honest accounting of what those eight documents leave genuinely open.
