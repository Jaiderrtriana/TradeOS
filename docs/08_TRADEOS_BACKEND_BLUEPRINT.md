# TRADEOS_BACKEND_BLUEPRINT.md

**Document Status:** CANONICAL AND FROZEN — the official backend implementation blueprint of TradeOS.
**Version:** 1.1
**Last Updated:** 2026-07-24
**Dependencies:** all seven documents listed above. This document redesigns none of them. Where `TRADEOS_SYSTEM_ARCHITECTURE.md` already answered a question at the architectural level (Modular Monolith, Clean Architecture, module boundaries, event dispatch mechanism, technology choices), this document does not re-derive that answer — it applies it one level deeper, into modules, use cases, domain services, repositories, and their interactions.
**Scope:** a technology-agnostic implementation blueprint — module structure, use cases, domain services, repositories, validation, events, transactions, background processing, observability, error handling, security, performance, testing, folder organization, and traceability — detailed enough for module-by-module implementation without further architectural decisions.
**Out of Scope:** source code, framework-specific syntax (NestJS, FastAPI, or otherwise), controllers, DTOs, repository implementations, SQL, migrations, or configuration files. Any point in this document that is not a mechanical translation of an already-frozen decision is registered as an Open Question (Section 21), never invented.
**Is Not:** a replacement for `TRADEOS_SYSTEM_ARCHITECTURE.md`. That document remains canonical for architectural style, quality attribute priorities, and technology decisions; this document is downstream of it.

---

## 1. Backend Principles

Engineering-level principles governing backend implementation — narrower and more tactical than `TRADEOS_SYSTEM_ARCHITECTURE.md`'s Architectural Principles (Section 1 there), which this list applies rather than restates.

1. **Domain First.** The Domain layer of every module is written before, and independent of, any framework or infrastructure concern — exactly as the reference `EvaluationEngine` implementation already demonstrates (testable with nothing but a test runner, `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 2.1).
2. **Modular Monolith.** One deployable, internally modularized by Bounded Context (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-01). This document does not reopen that decision — every module below assumes it.
3. **Clean Architecture, Strictly Directional.** Presentation → Application → Domain ← Infrastructure, one direction only (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 2.1). A Domain class importing an Infrastructure class is a defect, not a shortcut.
4. **Dependency Inversion.** The Domain layer defines the interfaces (e.g., a Repository interface) that Infrastructure implements — never the reverse. This is what keeps Domain testable without a database (Section 15).
5. **Single Responsibility per Module.** One module, one Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 4), one reason to change.
6. **Explicit Boundaries.** A module may only call another module's published Application-layer interface — never its Domain or Infrastructure layers directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3.3).
7. **Thin Presentation, Rich Domain/Application.** The Presentation layer maps HTTP to a Use Case call and a Use Case result back to HTTP — nothing else. Every business rule, every Domain Invariant check, lives in the Domain or Application layer, never in a route handler.
8. **Event-Driven Internally, Synchronous by Default.** Domain Events (Section 8) are always published; whether anything reacts to them today is separate from whether they exist (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 6.1).
9. **Configuration Over Hardcoding.** Anything the Evaluation Engine reads to compute a score — criteria, weights, profiles — is data (`TRADEOS_DOMAIN_MODEL.md` Section 8.2), never a code constant, exactly as `TRADEOS_DATABASE_DESIGN.md` Section 7 already committed to.
10. **Testability First.** The Domain layer, and the Evaluation module specifically, carry the highest test coverage bar in the system (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8's testing row) — this is a direct, non-negotiable consequence of Correctness being this project's top-ranked quality attribute (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9).

---

## 2. Backend Architecture

This section applies `TRADEOS_SYSTEM_ARCHITECTURE.md` Sections 2–7 one level deeper. It introduces no new architectural decision.

### 2.1 Overall Architecture
Confirmed, not redesigned: a Modular Monolith (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-01), one process, internally organized by Bounded Context (Section 3 of that document).

### 2.2 Application Layers (per module)
```
Presentation  →  Application (Use Cases)  →  Domain (entities, invariants, domain services)  ←  Infrastructure (repositories, external calls)
```
Identical to `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 2.1 — restated here as the layer each subsequent section of this document (Use Cases, Section 4; Domain Services, Section 5; Repositories, Section 6) is written against.

### 2.3 Bounded Context Implementation
Each Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 4) is one backend module (Section 3), matching the Postgres schema of the same name (`TRADEOS_DATABASE_DESIGN.md` Section 2.2) and the API module of the same name (`TRADEOS_API_SPECIFICATION.md` Section 5) — the same boundary, now enforced a fourth time, at the code-organization level.

### 2.4 Dependency Direction
Strictly inward: Presentation depends on Application, Application depends on Domain, Infrastructure depends on Domain (implementing its interfaces) — Domain depends on nothing (Principle 3, Section 1). Across modules, a dependency may only target another module's Application-layer interface (Principle 6).

### 2.5 Module Interaction
Identical to `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4 (Bounded Context Interactions) — restated per-module in Section 3 of this document with the concrete Use Cases (Section 4) that realize each interaction.

### 2.6 Request Lifecycle
```
1. Presentation layer receives an HTTP request (`TRADEOS_API_SPECIFICATION.md` Section 6 endpoint)
2. Presentation authenticates the request (Section 13) and maps the request body to a Use Case input
3. Application layer's Use Case (Section 4) executes:
   a. Loads any aggregate(s) needed via their Repository (Section 6)
   b. Invokes Domain logic / Domain Services (Section 5), which enforce invariants (Section 7)
   c. Persists the result via the Repository, within one transaction (Section 9)
   d. Publishes any resulting Domain Event(s) (Section 8), in the same transaction
4. Application layer returns a result (success value or a specific failure)
5. Presentation layer maps that result to the HTTP response shape (`TRADEOS_API_SPECIFICATION.md` Section 6/8) and status code
```

### 2.7 Command Flow vs. Query Flow
- **Commands** (any write — `POST`/`PATCH`/`DELETE` per `TRADEOS_API_SPECIFICATION.md` Section 3.4) always go through a full Use Case (Section 4): invariant checks, transaction, event publication.
- **Queries** (`GET`) may use a lighter path directly from Presentation to a Repository's read method when no business logic beyond data shaping is involved (e.g., `GET /trades` listing) — but never bypass a module's Application-layer boundary (Principle 6) to reach another module's Repository directly. A query that requires real computation (Statistics, Mistake ranking) still goes through its owning module's Application-layer service (Domain Model Section 12.2/12.3), never a raw cross-module query.

### 2.8 Transaction Boundaries
One Use Case, one transaction (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03, generalized here to every Use Case, not only Trade registration) — detailed fully in Section 9.

### 2.9 Error Propagation
A Domain Invariant violation raises a specific, named exception in the Domain layer (Section 7); the Application layer lets it propagate (never swallows or reinterprets it); the Presentation layer is the only place it is translated into the API's error envelope (`TRADEOS_API_SPECIFICATION.md` Section 8) — full detail in Section 12.

### 2.10 Logging Strategy
Every Use Case's entry, business outcome, and any Domain Event it publishes are logged with a shared correlation ID (Section 11) — detailed fully there.

### 2.11 Future Extraction into Services
Unchanged from `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.3: Evaluation and Analytics are the most likely first candidates for extraction into their own deployed service, precisely because this document's module boundaries (Section 3) already give each module a self-contained Application-layer contract with nothing informal crossing it.

---

## 3. Module Blueprint

Each module corresponds 1:1 to a Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 4), a Postgres schema (`TRADEOS_DATABASE_DESIGN.md` Section 3), and an API module (`TRADEOS_API_SPECIFICATION.md` Section 5).

### 3.1 Identity (Authentication + Users)
- **Purpose:** who is calling.
- **Responsibilities:** credential verification, token issuance/refresh/revocation, the user's own account record.
- **Dependencies:** none on other business modules (Generic Domain, `TRADEOS_DOMAIN_MODEL.md` Section 3.3).
- **Owned Aggregates:** `UserAccount` (`TRADEOS_DOMAIN_MODEL.md` Section 8.11).
- **Consumed Aggregates:** none.
- **Published Events:** none named in `TRADEOS_DOMAIN_MODEL.md` Section 11 — registered as **Open Question BE-1** (Section 21): should account creation/login raise Domain Events for future audit/security tooling?
- **Consumed Events:** none.
- **Configuration Owned:** none (no business configuration here).
- **Persistence Owned:** `identity` schema (`TRADEOS_DATABASE_DESIGN.md` Section 6.1).
- **External Dependencies:** a password-hashing library (implementation detail, not named here).
- **Future Extensibility:** OAuth/SSO, API Keys (Section 18) attach here without changing other modules.

### 3.2 Preferences
- **Purpose:** how the app feels to one user.
- **Responsibilities:** theme, language, notification settings.
- **Dependencies:** Identity (owns the `user_id` it's keyed on).
- **Owned Aggregates:** `UserPreferences` (`TRADEOS_DOMAIN_MODEL.md` Section 8.12).
- **Persistence Owned:** `preferences` schema (`TRADEOS_DATABASE_DESIGN.md` Section 6.2).
- **Future Extensibility:** none of substance — a Generic Domain by design (`TRADEOS_DOMAIN_MODEL.md` Section 3.3).

### 3.3 Trading
- **Purpose:** the Trade lifecycle.
- **Responsibilities:** register, amend, close, soft-delete Trades; own their Checklist/Evaluation Snapshots and tagged Mistakes.
- **Dependencies:** Evaluation (synchronous call at registration/re-evaluation, `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4); Configuration (indirectly, via Evaluation); Catalogs (validates referenced Setup/Session/Strategy/Entry Trigger/Mistake Tag IDs exist and are active at write time).
- **Owned Aggregates:** `Trade`, and (as owned child data) `ChecklistSnapshot`, `EvaluationSnapshot`, `evaluation_snapshot_breakdowns` (`TRADEOS_DOMAIN_MODEL.md` Section 7; storage placement justified in `TRADEOS_DATABASE_DESIGN.md` Section 3.1.1).
- **Consumed Aggregates:** `CatalogEntry` (by reference, read-only), the result of `EvaluationSnapshot` computation (produced by Evaluation, persisted by Trading).
- **Published Events:** `TradeRegistered`, `TradeEvaluated`, `TradeClosed`, `TradeAmended`, `MistakeTagged` (`TRADEOS_DOMAIN_MODEL.md` Section 11).
- **Consumed Events:** none today.
- **Configuration Owned:** none.
- **Persistence Owned:** `trading` schema.
- **External Dependencies:** none in v1.
- **Future Extensibility:** Broker Integration attaches upstream of this module's `RegisterTrade` Use Case (Section 18), never inside it.

### 3.4 Evaluation
- **Purpose:** the Core Domain — compute Confidence/Quality/Execution/Market Context/Bias.
- **Responsibilities:** run the `EvaluationEngine` domain service (Section 5) against supplied facts and the active Configuration.
- **Dependencies:** Configuration (reads active/specified `ScoringConfiguration`).
- **Owned Aggregates:** none — a pure domain service module (`TRADEOS_DOMAIN_MODEL.md` Section 12.1; confirmed at the storage layer too, `TRADEOS_DATABASE_DESIGN.md` Section 3, "three modules deliberately have no tables").
- **Consumed Aggregates:** `ScoringCriterion`, `ScoringWeight`, `ScoringConfiguration` (read-only, from Configuration); `ChecklistSnapshot`/`Trade` facts (passed in by Trading, never fetched independently by Evaluation).
- **Published Events:** none of its own — `TradeEvaluated` is published by Trading, since Trading owns the persisted `EvaluationSnapshot` (Section 3.3).
- **Consumed Events:** none.
- **Configuration Owned:** none (reads Configuration's, owns none itself).
- **Persistence Owned:** none.
- **Future Extensibility:** a sixth Engine (Section 18) is an addition to this module's domain logic plus a Configuration data change — no new module.

### 3.5 Configuration
- **Purpose:** the versionable source of truth driving Evaluation, plus shared reference Catalogs.
- **Responsibilities:** manage `ScoringCriterion`/`ScoringWeight`/`ScoringConfiguration` versions and their publish lifecycle; manage `CatalogEntry` (Setups, Sessions, Strategies, Entry Triggers, Mistake Tags — canonical taxonomy ownership per `TRADEOS_DATABASE_DESIGN.md` Section 3.1, 6.8).
- **Dependencies:** none on other business modules — the most upstream context (`TRADEOS_DOMAIN_MODEL.md` Section 4.3).
- **Owned Aggregates:** `ScoringConfiguration` (with its `ScoringCriterion`/`ScoringWeight`), `Catalog`/`CatalogEntry`.
- **Published Events:** `ScoringConfigurationChanged`, `CatalogEntryDeactivated`.
- **Consumed Events:** none.
- **Configuration Owned:** all of it — this module's entire purpose.
- **Persistence Owned:** `configuration` schema.
- **Future Extensibility:** a new Scoring Profile or Engine Type (Section 18) is a new row here, never a schema or module change.

### 3.6 Catalogs
Modeled here as a **sub-module of Configuration**, not a separate top-level module — `TRADEOS_API_SPECIFICATION.md` Section 5 lists Catalogs as its own API module for URL clarity (`/catalogs` vs. `/configuration/...`), but `TRADEOS_DOMAIN_MODEL.md` Section 4.3 and `TRADEOS_DATABASE_DESIGN.md` Section 3 both place Catalog ownership inside the Configuration Bounded Context. This document follows the Domain Model: one backend module (Configuration, Section 3.5), exposing two API surfaces.

### 3.7 Playbook
- **Purpose:** setup documentation and live performance attribution.
- **Responsibilities:** manage `PlaybookSetup` definitions and attachments; compose Statistics for the performance view.
- **Dependencies:** Statistics (calls its Application-layer service for by-dimension performance, `TRADEOS_DOMAIN_MODEL.md` Section 12.2); Configuration (validates the linked `CatalogEntry` is `kind=setup`).
- **Owned Aggregates:** `PlaybookSetup`.
- **Consumed Aggregates:** `CatalogEntry` (reference), Statistics output (read-only, never stored, `TRADEOS_DOMAIN_MODEL.md` Section 8.8).
- **Published Events:** `PlaybookSetupUpdated`.
- **Persistence Owned:** `playbook` schema.
- **Future Extensibility:** Playbook version history (Section 18) is additive to this module alone.

### 3.8 Mistakes (Mistake Tracking)
- **Purpose:** frequency/cost/priority ranking of tagged errors.
- **Responsibilities:** compute ranking on demand from Trading's `trade_mistakes` and Configuration's Mistake Tag catalog.
- **Dependencies:** Trading (read-only), Configuration (read-only, for tag names/metadata).
- **Owned Aggregates:** none (`TRADEOS_DATABASE_DESIGN.md` Section 3.1's confirmed ownership split: Configuration owns the taxonomy, this module owns only derived analytics, storing none of it either).
- **Persistence Owned:** none.
- **Future Extensibility:** none of substance beyond richer ranking heuristics, which remain internal to this module's domain service (`MistakePriorityRankingService`, Section 5).

### 3.9 Statistics (Analytics)
- **Purpose:** performance analytics, all-time and rolling.
- **Responsibilities:** compute Win Rate/Expectancy/Profit Factor/Average R, by any dimension or window, always freshly.
- **Dependencies:** Trading, Evaluation (both read-only).
- **Owned Aggregates:** none (`TRADEOS_DOMAIN_MODEL.md` KDD-04 — never a source of truth).
- **Persistence Owned:** none.
- **Future Extensibility:** the Intelligence/Pattern Discovery domain (Section 18) is a new domain service alongside `StatisticsAggregationService`, reading the same data, inside what could remain this same module or be split out later — not a redesign either way.

### 3.10 Journal
- **Purpose:** qualitative reflection.
- **Responsibilities:** create/read/edit/soft-delete `JournalEntry`, trade-scoped or period-scoped.
- **Dependencies:** Trading (validates a supplied `trade_id` exists and is owned by the caller).
- **Owned Aggregates:** `JournalEntry`.
- **Persistence Owned:** `journal` schema.

### 3.11 Reports
**Not a real module in v1.** Named in the prompt for this document; no confirmed Domain Model entity or API module exists for it (`TRADEOS_API_SPECIFICATION.md` API-6). Listed here only to state explicitly that it is reserved namespace (Section 18), not a module to implement now.

### 3.12 Infrastructure / Platform (Cross-Cutting)
- **Purpose:** shared technical concerns with no business meaning — the event dispatcher, the correlation-ID/logging middleware, the authentication middleware.
- **Responsibilities:** dispatch Domain Events to any subscriber (Section 8); write to `platform.event_log`; issue/verify JWTs at the request boundary.
- **Dependencies:** called by every module; depends on none of them.
- **Owned Aggregates:** none in the business sense; owns the `platform.event_log` table (`TRADEOS_DATABASE_DESIGN.md` Section 6.18).
- **Future Extensibility:** the in-process dispatcher here is the exact seam that becomes an async message bus later (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 6.2) without any publishing module changing.

### 3.13 Future AI, Future Notifications
Reserved (`TRADEOS_DOMAIN_MODEL.md` Section 17; `TRADEOS_API_SPECIFICATION.md` Section 17) — no module structure designed here beyond confirming both would be new, downstream-only modules consuming Domain Events (Section 8) and Statistics output, never becoming a source of truth for any existing aggregate (Section 18 elaborates).

---

## 4. Use Case Blueprint

**Scoping note**, consistent with the precedent already set in `TRADEOS_API_SPECIFICATION.md` Section 6 and `TRADEOS_FRONTEND_BLUEPRINT.md` Section 5: the seven Use Cases most illustrative of a recurring pattern are specified in full. The remainder are specified compactly, inheriting the same conventions.

### 4.1 RegisterTrade
- **Purpose:** capture a new Trade and produce its initial Evaluation.
- **Actor:** the authenticated trader.
- **Preconditions:** caller is authenticated; referenced Catalog entries (if any) exist and are active.
- **Business Flow:** validate shape → validate INV-TRADE-01 (stop placement) → validate INV-TRADE-02 (if `result`+`exit_price` both supplied) → call Evaluation's Application-layer service with the supplied `checklist_answers` and the active `ScoringConfiguration` → persist `Trade` + `ChecklistSnapshot` + `EvaluationSnapshot` (+ breakdown rows) in one transaction → publish `TradeRegistered`, then `TradeEvaluated`.
- **Success Result:** the persisted Trade with its computed properties and current Evaluation.
- **Failure Cases:** `422` shape/invariant violation (no persistence, no event); referenced Catalog entry inactive or missing (`422`).
- **Business Rules Applied:** INV-TRADE-01, INV-TRADE-02, INV-WEIGHT-01 (missing checklist answers handled gracefully by the Evaluation Engine itself).
- **Events Published:** `TradeRegistered`, `TradeEvaluated`.
- **Events Consumed:** none.
- **Transaction Scope:** one transaction covering Trade + ChecklistSnapshot + EvaluationSnapshot + breakdown rows + both events' `platform.event_log` writes.
- **Audit Logging:** both events logged with the acting `user_id` and a correlation ID (Section 11).
- **Future Extensions:** a Broker Integration's automated import calls this same Use Case (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 13) — it does not bypass it.

### 4.2 CloseTrade
- **Purpose:** transition a Trade to a terminal Result.
- **Actor:** the authenticated trader.
- **Preconditions:** the Trade exists, is owned by the caller, and is currently `Open`.
- **Business Flow:** validate `result`+`exit_price` supplied together (INV-TRADE-02) → validate the Trade is not already closed (state conflict otherwise) → update Trade's result/exit_price/mfe_price/mae_price/closed_at → publish `TradeClosed`.
- **Success Result:** the updated Trade, now with computable `r_multiple`/MFE/MAE/Captured %/Potential Left.
- **Failure Cases:** `409` if already closed; `422` if `result`/`exit_price` incomplete.
- **Business Rules Applied:** INV-TRADE-02.
- **Events Published:** `TradeClosed`.
- **Transaction Scope:** one transaction (Trade update + event log write).
- **Future Extensions:** none named yet — a candidate seam for a future Notification ("your trade closed") to attach to, without this Use Case changing.

### 4.3 ReevaluateTrade
- **Purpose:** the explicit, deliberate re-scoring action (`TRADEOS_DOMAIN_MODEL.md` Section 8.2 — never automatic).
- **Actor:** the authenticated trader.
- **Preconditions:** the Trade exists and is owned by the caller; the target `ScoringConfiguration` version (specified or defaulted to currently-published) has `status = published`.
- **Business Flow:** load the Trade's existing `ChecklistSnapshot` (unchanged) → call Evaluation's service against the specified Configuration version → insert a **new** `EvaluationSnapshot` row with `is_current = true` → flip the prior row's `is_current` to `false` (never delete it) → publish `TradeEvaluated`.
- **Success Result:** the new, current Evaluation Snapshot; the prior one remains queryable via history.
- **Failure Cases:** `422` if the specified configuration version is not published; `404` if the Trade or version doesn't exist.
- **Business Rules Applied:** Domain Invariant DI-06 (snapshots are superseded, never mutated).
- **Events Published:** `TradeEvaluated`.
- **Transaction Scope:** one transaction (new snapshot insert + prior snapshot flag flip + event log write) — both changes must succeed or neither does, since a half-applied "two current snapshots" or "zero current snapshots" state would itself be an invariant violation.
- **Future Extensions:** this Use Case is, today, strictly per-Trade — see **Open Question BE-10** (Section 21) on whether a bulk variant was ever meant to exist alongside it.

### 4.4 PublishScoringConfigurationVersion
- **Purpose:** the single most consequential Configuration action.
- **Actor:** the authenticated trader (today; a future admin role if Product Bible Open Question 2 resolves toward multi-user).
- **Preconditions:** the target version has `status = draft`; every `ScoringCriterion` referenced by an active `ScoringWeight` in this version is itself active.
- **Business Flow:** validate the precondition above → set this version's `status = published`, `published_at = now()` → set the previously-published version's `status = superseded` → publish `ScoringConfigurationChanged`.
- **Success Result:** the version, now published; the prior one, now superseded — both retained forever.
- **Failure Cases:** `409` if the target version isn't a draft; `422` if it references an inactive criterion.
- **Business Rules Applied:** Domain Invariant DI-06/DI-07 (versioned, never mutated in place; never retroactively reinterprets past snapshots).
- **Events Published:** `ScoringConfigurationChanged`.
- **Transaction Scope:** one transaction (both version status updates + event log write) — the two status flips must be atomic, since a state with two "published" versions or zero would itself be invalid.
- **Explicitly Not Triggered:** any re-evaluation of existing Trades — that remains `ReevaluateTrade` (Section 4.3), called separately, per Trade, by explicit user action.

### 4.5 PreviewEvaluation
- **Purpose:** compute scores from supplied answers without persisting anything.
- **Actor:** the authenticated trader (still authenticated, `TRADEOS_API_SPECIFICATION.md` Section 6.5, even though nothing is saved).
- **Preconditions:** none beyond authentication.
- **Business Flow:** call the `EvaluationEngine` domain service directly with the supplied answers, profile, and configuration version — no Repository call, no transaction, no event.
- **Success Result:** the computed scores/grades/breakdown, entirely ephemeral.
- **Failure Cases:** `422` for an unrecognized profile or malformed answers.
- **Events Published:** none — this is the one Use Case in this document that touches no aggregate and publishes nothing, by design (`TRADEOS_DOMAIN_MODEL.md` Section 12.1's "pure function, holds no state").
- **Transaction Scope:** none required.

### 4.6 TagMistake
- **Purpose:** attach a Mistake Tag to a Trade.
- **Actor:** the authenticated trader.
- **Preconditions:** the Trade is owned by the caller; the referenced `CatalogEntry` exists, is `kind=mistake_tag`, and is active.
- **Business Flow:** insert a `trade_mistakes` row → publish `MistakeTagged`.
- **Failure Cases:** `422` if the catalog entry isn't a mistake tag or is inactive; `404` if the Trade doesn't exist/isn't owned.
- **Events Published:** `MistakeTagged`.
- **Transaction Scope:** one transaction (junction row insert + event log write).

### 4.7 CreateJournalEntry
- **Purpose:** record a reflection.
- **Actor:** the authenticated trader.
- **Preconditions:** exactly one of `trade_id` or (`period_start` + `period_end`) supplied; if `trade_id` is supplied, it must be owned by the caller.
- **Business Flow:** validate the exactly-one-reference rule → persist the entry.
- **Failure Cases:** `422` if both or neither reference type supplied.
- **Events Published:** none named in `TRADEOS_DOMAIN_MODEL.md` Section 11 for Journal — consistent, not an oversight.
- **Transaction Scope:** one transaction (single-row insert).

### 4.8 Remaining Use Cases (Compact)

| Use Case | Module | Business Rules Applied | Events Published |
|---|---|---|---|
| AmendTrade | Trading | INV-TRADE-01/02 re-validated against proposed full state | `TradeAmended` |
| DeleteTrade (soft) | Trading | none beyond ownership | none named — see Open Question BE-2 (Section 21) |
| CreateScoringCriterion / UpdateScoringCriterion | Configuration | `max_value >= min_value`; `engine_type_code` immutable after creation | none named — see Open Question BE-3 |
| DeactivateScoringCriterion | Configuration | Domain Invariant DI-10 (deactivate, never delete) | none named — see Open Question BE-3 |
| CreateDraftConfigurationVersion / UpdateDraftWeights | Configuration | draft-only mutability (`TRADEOS_DATABASE_DESIGN.md` Section 6.6) | none named — see Open Question BE-3 |
| CreateCatalogEntry / UpdateCatalogEntry / DeactivateCatalogEntry | Configuration | `(kind, name)` uniqueness; DI-10 | `CatalogEntryDeactivated` (deactivate only) |
| CreatePlaybookSetup / UpdatePlaybookSetup / DeprecatePlaybookSetup | Playbook | 1:1 with a `kind=setup` Catalog entry | `PlaybookSetupUpdated` |
| GetMistakeRanking | Mistakes | none (pure read) | none |
| GetStatisticsOverview / GetStatisticsByDimension / GetRollingStatistics | Statistics | none (pure read) | none |
| UpdateJournalEntry / DeleteJournalEntry (soft) | Journal | reference type immutable after creation | none |
| Register / Login / RefreshToken / Logout | Identity | email uniqueness | none named — Open Question BE-1 |
| UpdatePreferences | Preferences | enum membership only | none |

**Open Question BE-3** (Section 21) applies uniformly to every Configuration write above: `TRADEOS_DOMAIN_MODEL.md` Section 11 names `ScoringConfigurationChanged` and `CatalogEntryDeactivated` but no event for creating or editing an individual criterion/weight/catalog entry short of deactivation or publishing — this document does not invent one.

---

## 5. Domain Services Blueprint

All four already named in `TRADEOS_DOMAIN_MODEL.md` Section 12 — this section adds only their backend implementation contract, not new behavior.

| Service | Responsibilities | Inputs | Outputs | Dependencies | Stateless? | Reuse |
|---|---|---|---|---|---|---|
| `EvaluationEngine` | Compute all five Engines' scores | Checklist/Trade facts, active `ScoringConfiguration`, `ScoringProfile` | `EvaluationSnapshot`-shaped result (scores, grades, breakdown) | None beyond its inputs (pure function, `TRADEOS_DOMAIN_MODEL.md` Section 12.1) | Yes — no internal state, safe to invoke concurrently | `RegisterTrade`, `ReevaluateTrade`, `PreviewEvaluation` (Section 4) |
| `StatisticsAggregationService` | Compute Win Rate/Expectancy/Profit Factor/Average R over any Trade set | A Trade collection (all-time, windowed, or dimension-filtered) | Aggregate metrics | Reads via Trading's Repository (read-only) | Yes | `GetStatisticsOverview/ByDimension/Rolling`, `PlaybookSetup` performance composition |
| `MistakePriorityRankingService` | Frequency/cost/priority per Mistake Tag | Trades referencing each tag | Ranked list | Reads via Trading + Configuration Repositories | Yes | `GetMistakeRanking` |
| `PlaybookRecommendationService` | Surface promotion/de-emphasis candidates | `StatisticsAggregationService` output grouped by setup | Suggestions (never auto-applied) | `StatisticsAggregationService` | Yes | Not yet wired to a confirmed endpoint — see Open Question BE-4 (Section 21) |

**Lifecycle:** all four are constructed fresh per invocation (or per request) — none holds state across calls, consistent with Principle 1 (Domain First) and the reference `EvaluationEngine` implementation already built.

---

## 6. Repository Blueprint

One repository per Aggregate Root (`TRADEOS_DOMAIN_MODEL.md` Section 7), each implementing an interface defined in its module's Domain layer (Principle 4, Section 1) and implemented in that module's Infrastructure layer.

| Repository | Owned Aggregate | Key Reads | Key Writes | Optimized For | Consistency Rule | Caching | Concurrency |
|---|---|---|---|---|---|---|---|
| `TradeRepository` | `Trade` (+ owned Checklist/Evaluation Snapshots) | by ID; filtered/sorted/paginated list (`TRADEOS_API_SPECIFICATION.md` Section 7); all snapshots for a Trade | insert (with snapshots, one transaction); update (amend/close); soft-delete | The composite index on `(strategy_id, setup_id, session_id, direction)` and the `entered_at` index (`TRADEOS_DATABASE_DESIGN.md` Section 10.1) | Never returns a soft-deleted row by default | None — always fresh (Section 2.7 of the Frontend Blueprint applies equally here: the backend itself never caches a Trade as a shortcut) | Single-user today; a future concurrent-edit conflict (two amendments racing) is an unaddressed Open Question — BE-5 (Section 21) |
| `ScoringConfigurationRepository` | `ScoringConfiguration` (+ `ScoringCriterion`, `ScoringWeight`) | active/published version; a specific historical version by ID; criteria filtered by engine | insert new draft version + weights; publish (status flips, Section 4.4) | The composite index on `(configuration_version_id, profile_code)` (`TRADEOS_DATABASE_DESIGN.md` Section 10.1) | Never updates a `published` or `superseded` version's rows | Short-TTL safe (Section 2.7 of the Frontend Blueprint) since changes are rare and deliberate | Two concurrent "publish" calls on the same draft — Open Question BE-6 |
| `CatalogRepository` | `Catalog`/`CatalogEntry` | by kind; by ID | insert; update metadata; deactivate (never delete) | The `kind` index | Enforces `(kind, name)` uniqueness | Short-TTL safe | Low risk — infrequent writes |
| `PlaybookSetupRepository` | `PlaybookSetup` | by ID; list; by linked catalog entry | insert; update; deprecate; attachment add/remove | — | Enforces 1:1 with its `catalog_entry_id` | Not cached (performance data composed live anyway) | Low risk |
| `JournalEntryRepository` | `JournalEntry` | by ID; by `trade_id`; by date range | insert; update; soft-delete | `trade_id` and `(period_start, period_end)` indexes | Enforces exactly-one-reference-type at write time | None | Low risk |
| `UserAccountRepository` | `UserAccount` | by ID; by email (login) | insert; update email | Unique index on `email` | Never returns `password_hash` to any caller outside the Identity module's own authentication check | None | Low risk |
| `UserPreferencesRepository` | `UserPreferences` | by `user_id` | insert (at registration); update | Unique index on `user_id` | 1:1 with `UserAccount` | Short-TTL safe | Low risk |

**Note on Mistakes and Statistics:** neither module has a repository of its own (Section 3.8, 3.9) — both read through `TradeRepository` and `CatalogRepository`'s existing read methods, never introducing a parallel data-access path.

---

## 7. Validation Blueprint

Four layers, matching `TRADEOS_API_SPECIFICATION.md` Section 9 exactly, now mapped to where each is implemented in the backend.

| Layer | Where Implemented | Example |
|---|---|---|
| **Request/shape validation** | Presentation layer (request schema check, before a Use Case is even invoked) | Missing required `entry_price` on `POST /trades` |
| **Business validation (Domain Invariants)** | Domain layer, inside the aggregate itself (e.g., `Trade`'s own invariant check) | INV-TRADE-01, checked by the `Trade` entity's own construction/mutation logic, not by the Use Case orchestrating it |
| **Database constraints** | Infrastructure layer / the database itself (`TRADEOS_DATABASE_DESIGN.md` Section 6) | The `(kind, name)` unique constraint on `catalog_entries` |
| **Authorization / ownership** | Application layer, as the first step of every Use Case (Section 4), before any Domain logic runs | Confirming the caller's `user_id` matches the Trade's `user_id` |
| **Configuration validation** | Domain layer, inside `ScoringConfiguration`/`PublishScoringConfigurationVersion` (Section 4.4) | Rejecting a publish if an active weight references an inactive criterion |
| **Cross-module validation** | Application layer, via a call to the owning module's Application-layer interface — never a direct cross-schema query | `RegisterTrade` confirming a supplied `setup_id` is an active Catalog entry, by calling Configuration's interface, not by querying `configuration.catalog_entries` directly from the Trading module |

**Error Strategy:** a violation at any layer above raises a specific exception type; the Presentation layer (and only the Presentation layer) translates it into the API's error envelope and HTTP status (`TRADEOS_API_SPECIFICATION.md` Section 8) — detailed fully in Section 12.

---

## 8. Domain Events Blueprint

All eight events already named in `TRADEOS_DOMAIN_MODEL.md` Section 11. This section adds their backend dispatch contract.

| Event | Publisher (Module) | Payload (representative) | Purpose | Current Subscribers |
|---|---|---|---|---|
| `TradeRegistered` | Trading | `trade_id`, `user_id`, core facts | New Trade exists | None (logged only) |
| `TradeEvaluated` | Trading | `trade_id`, `evaluation_snapshot_id`, `configuration_version_id` | A snapshot was produced (initial or re-evaluation) | None |
| `TradeClosed` | Trading | `trade_id`, `result`, `exit_price` | Trade reached a terminal state | None |
| `TradeAmended` | Trading | `trade_id`, changed fields, before/after | A correction was made | None |
| `MistakeTagged` | Trading | `trade_id`, `catalog_entry_id` | A Mistake was attached | None |
| `ScoringConfigurationChanged` | Configuration | `new_version_id`, `superseded_version_id` | A new configuration went live | None |
| `PlaybookSetupUpdated` | Playbook | `playbook_setup_id`, changed fields | A setup's definition changed | None |
| `CatalogEntryDeactivated` | Configuration | `catalog_entry_id`, `kind` | An entry was deactivated | None |

**Ordering:** events are published in the order their triggering facts became true within one Use Case (e.g., `TradeRegistered` before `TradeEvaluated`, Section 4.1) — no cross-Trade ordering guarantee is needed or provided, since each Trade's events are independent.

**Idempotency:** the events themselves are simple facts appended to `platform.event_log` (`TRADEOS_DATABASE_DESIGN.md` Section 6.18) — they carry no idempotency requirement of their own. The *action* that triggers them is protected by the API's `Idempotency-Key` mechanism (`TRADEOS_API_SPECIFICATION.md` Section 3.6), which prevents the triggering Use Case from running twice, not the event system from delivering twice.

**Retry Policy:** none needed today — dispatch is in-process and synchronous, within the same transaction as the domain write (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 6.1). There is no network hop to retry.

**Failure Handling:** if writing an event to `platform.event_log` fails, the entire transaction (including the domain write that triggered it) rolls back — an event and the fact it describes are never allowed to disagree about whether something happened (Section 9).

**Future Subscribers:** every event above is the exact, already-identified seam for Future Reserved Domains (`TRADEOS_DOMAIN_MODEL.md` Section 17) — AI Coaching would subscribe to `TradeEvaluated`/`TradeClosed`; a future Notification module to `TradeClosed`/`CatalogEntryDeactivated`; Pattern Discovery to the same stream Analytics already reads from directly (Section 18 elaborates).

---

## 9. Transaction Blueprint

- **Atomic Operations:** one Use Case (Section 4) is one transaction — never split across multiple round trips to the database, and never left partially applied. This generalizes `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03 (originally stated only for Trade registration) to every Use Case in this document.
- **Rollback Strategy:** any exception raised by any layer during a Use Case's execution rolls back the entire transaction — including any `platform.event_log` write already staged within it. An event is never left recorded for a domain change that didn't actually commit.
- **Consistency Guarantees:** strong consistency within a single aggregate's transaction (e.g., `Trade` + its snapshots). Cross-aggregate references (a Trade's `setup_id`) are validated at write time (Section 7) rather than relying on eventual consistency — there is no scenario in v1 where a Trade is allowed to reference a Catalog entry that doesn't yet exist.
- **Isolation Expectations:** standard read-committed isolation is sufficient at current scale (one confirmed user, `TRADEOS_PRODUCT_BIBLE.md` Section 4.2) — no write contention exists to protect against yet. **Open Question BE-5** (Section 21, also referenced in Section 6): what isolation level and conflict-resolution strategy is needed once concurrent edits become possible (multi-user, or even two browser tabs for one user) is not yet decided.
- **Long-Running Operations:** none exist (`TRADEOS_API_SPECIFICATION.md` Section 10) — no transaction in this document is expected to span more than one ordinary request's duration.
- **Future Distributed Transactions:** only becomes relevant if a module is extracted into its own deployed service (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.3) — at that point, the current single-transaction Use Cases that span what would become two services (none do today, since Evaluation and Analytics have no persistence of their own to coordinate) would need a saga or compensating-transaction pattern. Not designed now, per Architectural Principle 4 (Simplicity Until Proven Insufficient).

---

## 10. Background Processing

**None exists in v1** — consistent with `TRADEOS_API_SPECIFICATION.md` Section 10's confirmed "no Long Running Operations" position. This section registers future responsibilities only, per the prompt's own instruction not to implement them.

| Future Job | Responsibility | Triggered By | Depends On |
|---|---|---|---|
| AI Coach processing | Generate a conversational response or observation from Trade/Evaluation history | A user query, or (later) a subscribed Domain Event | The AI Coaching Future Reserved Domain (`TRADEOS_DOMAIN_MODEL.md` Section 17) |
| Report generation | Produce an exportable summary | A user request | The Reports module (currently unconfirmed, Section 3.11) |
| Notification delivery | Deliver an alert for a subscribed event | `TradeClosed`, `CatalogEntryDeactivated`, etc. | The Notifications Future Reserved Domain |
| Broker/Exchange import | Pull external trade data and call `RegisterTrade` (Section 4.1) on the caller's behalf | A schedule or webhook | The Broker Integration Future Reserved Domain |
| Data export | Produce a downloadable file of Trades/Statistics | A user request | Same open question as Report generation |
| Scheduled cleanup | E.g., expiring old, unused refresh tokens | A schedule | Identity module |
| **Bulk re-evaluation of historical Trades** | Re-score many/all Trades after a Configuration change | A user action, if this capability is ever built | **Open Question BE-10** (Section 21) — see the reasoning there; today only a per-Trade `ReevaluateTrade` (Section 4.3) exists anywhere in the seven frozen documents |

None of these has a chosen background-processing technology in this document (deliberately technology-agnostic, per this document's own mandate) — that choice belongs with whichever future document specifies the corresponding Future Reserved Domain in enough detail to need one.

---

## 11. Logging & Observability

Directly implements Architectural Principle 5 (`TRADEOS_SYSTEM_ARCHITECTURE.md`, Observability Is Not Optional) and the Quality Attributes Matrix's ranking of Reliability as the second-highest priority (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9).

- **Logging Philosophy:** the system must never fail silently. Every Use Case logs its entry, its outcome (success or a specific named failure), and every Domain Event it publishes.
- **Audit Logs:** `platform.event_log` (`TRADEOS_DATABASE_DESIGN.md` Section 6.18) is the audit trail — every Domain Event, who triggered it (`user_id`), and when.
- **Business Logs:** the same events, in human-readable log form, for operational visibility distinct from the durable audit table.
- **Technical Logs:** infrastructure-level concerns (a failed database connection, an unhandled exception) — always includes the correlation ID below.
- **Correlation IDs / Trace IDs:** a single ID is generated at the Presentation layer the moment a request arrives, threaded through every log line the request produces, and returned to the client inside the error envelope's `trace_id` field on failure (`TRADEOS_API_SPECIFICATION.md` Section 8) — the exact mechanism that lets a user-reported error be found in server logs.
- **Metrics:** per-endpoint latency, per-error-category rate, and — given Correctness's top ranking — Evaluation Engine computation time and outcome distribution (score ranges, grade distribution) as a business-health signal, not only a technical one.
- **Health Checks:** a basic liveness/readiness check, unauthenticated, outside the versioned `/api/v1` business surface entirely (e.g., `/healthz`) — registered here as a new, minor addition; **Open Question BE-7** (Section 21): this was not named in `TRADEOS_API_SPECIFICATION.md` and should be added there in a future revision, not silently assumed to exist by this document alone.
- **Monitoring Hooks:** the correlation ID and metrics above are the minimum surface a future monitoring/alerting tool would attach to — no specific tool is chosen here.
- **Future Observability:** if Evaluation or Analytics is ever extracted into its own service (Section 2.11), the correlation ID must propagate across that new network boundary — a requirement to carry forward at that time, not solved now.

---

## 12. Error Handling

| Category | Where Raised | Where Translated | Client-Facing Result |
|---|---|---|---|
| Validation (`VALIDATION_FAILED`) | Presentation layer (shape) or Domain layer (range) | Presentation layer | `422`, per-field `details` |
| Business/Invariant (`INVARIANT_VIOLATION`) | Domain layer | Presentation layer | `422`, `details` names the specific invariant ID (`TRADEOS_DOMAIN_MODEL.md` Section 15) |
| Authorization (`FORBIDDEN`/`NOT_FOUND`) | Application layer (ownership check, Section 7) | Presentation layer | `404` for Trades/Journal specifically (never `403`, to avoid confirming existence — `TRADEOS_API_SPECIFICATION.md` Section 8) |
| Conflict (`CONFLICT`) | Domain or Application layer (state check) | Presentation layer | `409` |
| Infrastructure errors (DB unreachable, etc.) | Infrastructure layer | A global exception handler at the Presentation boundary | `500`, `INTERNAL_ERROR`, generic message + `trace_id` — **never** the underlying exception's message or stack trace |
| Unexpected/unhandled exceptions | Anywhere | The same global handler | Same as above — this is the safety net, not a designed path |

**Recovery Strategy:** validation and business errors are always recoverable by the caller correcting input — no retry logic needed backend-side. Infrastructure errors are logged with full detail server-side (Section 11) and surfaced to the client with only the generic message and `trace_id`, consistent with never leaking internal detail (`TRADEOS_API_SPECIFICATION.md` Section 8).

**Logging Expectations:** every error, at every category, is logged with its correlation ID and enough detail to reproduce it — the `500` category specifically must never be under-logged just because the client-facing message is generic.

---

## 13. Security Blueprint

- **Authentication:** verified once, at the Presentation layer boundary, before any request reaches a Use Case — token-based, per `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-07 and `TRADEOS_API_SPECIFICATION.md` Section 4.
- **Authorization:** the single ownership rule (`TRADEOS_API_SPECIFICATION.md` Section 4.6), checked as the first step of every Use Case that touches owned data (Section 4) — never assumed satisfied by the Presentation layer alone.
- **Permission Checks:** today, reducible to the ownership rule above — no role/permission matrix exists yet (Generic Domain, least design effort, `TRADEOS_DOMAIN_MODEL.md` Section 3.4).
- **Ownership Validation:** implemented once, as a reusable check inside the Application layer, never duplicated per Use Case with slightly different logic (Principle 5, `TRADEOS_SYSTEM_ARCHITECTURE.md`).
- **Input Sanitization:** shape validation (Section 7) is the primary defense; free-text fields (`notes`, Journal `content`) are stored as-is and sanitized at render time by the frontend (`TRADEOS_FRONTEND_BLUEPRINT.md` Section 15) — the backend's responsibility is to never execute or interpret stored free text as anything other than data.
- **Rate Limiting Hooks:** applied at the Presentation layer, per authenticated user (`TRADEOS_API_SPECIFICATION.md` Section 12) — specific thresholds remain an operational tuning decision, not fixed here.
- **Secrets Handling:** database credentials, signing keys — environment-injected, never in source control (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1).
- **Future API Keys:** attach at the Presentation layer as an alternative authentication scheme for service-to-service callers (Section 18) — no business module changes.
- **Future OAuth:** replaces or supplements the Identity module's credential-verification step only — every other module is unaffected, since they only ever see "the current authenticated user."
- **Future Multi-User:** the ownership rule (above) extends from "owned by this user" to "owned by this user's workspace" — an extension of the same rule, not a new one, per `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.2's promised migration path.

---

## 14. Performance Blueprint

- **Caching Strategy:** Configuration and Catalog reads are safe to cache briefly server-side as well as client-side (`TRADEOS_API_SPECIFICATION.md` Section 15); Trades/Statistics/Evaluation are never cached as a source of truth (Domain Invariant DI-11) — matching `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04's deferral of Analytics caching specifically.
- **Read Optimization:** every Repository's query shape (Section 6) matches an index already specified in `TRADEOS_DATABASE_DESIGN.md` Section 10.1 — no query is written against an unindexed access pattern.
- **Write Optimization:** single-row, single-transaction writes throughout (Section 9) — no batching exists or is needed, consistent with `TRADEOS_API_SPECIFICATION.md` Section 15's explicit deferral of batch operations.
- **Indexes:** owned entirely by `TRADEOS_DATABASE_DESIGN.md` Section 10.1 — this document does not introduce a new one, only confirms every Repository method it describes has one to use.
- **Connection Pooling:** standard practice, sized conservatively for the confirmed single-user load (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2) — not a current tuning concern.
- **Batch Processing:** none in v1 (see above).
- **Memory Considerations:** the `EvaluationEngine`'s computation is lightweight and synchronous (a handful of criteria per engine, `TRADEOS_DATABASE_DESIGN.md` Section 7) — no special memory provisioning is needed at current or the confirmed 20,000-trade target scale.
- **Future Scalability:** the Statistics module recomputing over the full Trade history on every call is the one place growth could eventually require attention (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.1) — explicitly deferred until demonstrated necessary, not solved speculatively here.

---

## 15. Testing Blueprint

- **Testing Philosophy:** directly motivated by this project's own history (`PROJECT_AUDIT.md`) — nearly every costly defect found during the Excel's construction was a silent correctness failure, never a performance one. Testing exists to make that class of failure structurally impossible, not to hit a coverage number for its own sake.
- **Unit Tests:** the Domain layer, especially `EvaluationEngine` (Section 5), is unit-tested with zero infrastructure dependencies — exactly as the reference implementation's `test_evaluation_engine.py` already demonstrates. Every Domain Invariant (`TRADEOS_DOMAIN_MODEL.md` Section 15) has at least one test asserting it is enforced, and at least one asserting the specific historical bug it was introduced to prevent where one exists (e.g., the `round_half_up` rounding defect found and fixed during the reference implementation's own construction).
- **Integration Tests:** each Use Case (Section 4), tested end-to-end against a real (or realistic in-memory) database, verifying the full transaction — not just the Domain logic in isolation.
- **Repository Tests:** each Repository (Section 6) tested for its documented read/write behavior, including that deactivated Catalog entries and soft-deleted Trades are excluded from default queries but still resolvable by ID for historical reference (Domain Invariant DI-10).
- **Use Case Tests:** every success path and every named failure case in Section 4's table is a distinct test.
- **Domain Tests:** covered by Unit Tests above — called out separately here only to state that Domain tests carry the highest priority and coverage bar of any layer, per Principle 10 (Section 1).
- **Contract Tests:** verify that every endpoint's actual response shape matches `TRADEOS_API_SPECIFICATION.md` Section 6's documented shape exactly — the mechanical check that keeps that document's "OpenAPI readiness" claim (its Section 16) true over time.
- **Test Data Strategy:** seed data mirrors the real Catalog defaults already established in the Excel/reference implementation (the confirmed Setups, Sessions, Strategies, Entry Triggers, Mistake Tags) — never invented test-only categories that don't correspond to real business data.
- **Regression Testing:** every bug found and fixed during this project's history (`PROJECT_AUDIT.md`; the reference implementation's own `round_half_up` fix) has a permanent, named regression test — a bug is only considered fixed once it cannot silently reappear.
- **Coverage Expectations:** Domain layer (especially Evaluation) near-exhaustive; Application layer (Use Cases) one test per success/failure path; Infrastructure/Presentation layers pragmatic, focused on the contract (shape, status codes) rather than exhaustive input permutation.

---

## 16. Folder & Project Organization

Directly restates `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3's structure, at the level of detail needed to start implementation:

```
tradeos-backend/
├── modules/
│   ├── identity/            (Section 3.1)
│   │   ├── domain/              UserAccount entity, invariants
│   │   ├── application/         Register, Login, Refresh, Logout use cases (Section 4.8)
│   │   ├── infrastructure/      UserAccountRepository implementation (Section 6)
│   │   └── presentation/        this module's API routes
│   ├── preferences/         (Section 3.2)
│   ├── trading/             (Section 3.3)
│   │   ├── domain/              Trade, ChecklistSnapshot, EvaluationSnapshot (as owned data)
│   │   ├── application/         RegisterTrade, CloseTrade, ReevaluateTrade, AmendTrade,
│   │   │                        DeleteTrade, TagMistake (Section 4)
│   │   ├── infrastructure/      TradeRepository (Section 6)
│   │   └── presentation/
│   ├── evaluation/          (Section 3.4 — domain/application only; no infrastructure or persistence)
│   ├── configuration/       (Section 3.5, includes Catalogs sub-module per Section 3.6)
│   ├── playbook/            (Section 3.7)
│   ├── mistakes/            (Section 3.8 — no infrastructure; reads via trading/configuration's repositories)
│   ├── statistics/          (Section 3.9 — no infrastructure)
│   └── journal/             (Section 3.10)
├── shared_kernel/           Money, RMultiple, Score, Grade, Direction, TradeResult, EngineType
│                            (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3.2 — the one deliberate
│                             exception to strict module isolation)
└── platform/                Event dispatcher, event_log writer, auth middleware, logging/
                             correlation-ID middleware (Section 3.12)
```

**Naming Conventions:** module folder names match their Bounded Context name exactly (lowercase, matching the Postgres schema names in `TRADEOS_DATABASE_DESIGN.md` Section 2.2) — no module has a different name at the code level than at the database or API level.

**Dependency Rules:** enforced by Principle 6 (Section 1) — a module's `domain/` or `infrastructure/` folder is never imported from outside that module; only its `application/` layer's public interface is.

**Import Rules:** `shared_kernel` may be imported by any module's any layer (it contains no business logic of its own, only stable value shapes); `platform/` may be imported by any module's `application/` or `presentation/` layer (never by `domain/`, which must remain framework/infrastructure-free per Principle 1).

---

## 17. Component Interaction Blueprint

Following the exact flow named in this document's own source prompt, with responsibilities stated at each step:

```
Client
  │  (an HTTP request to a TRADEOS_API_SPECIFICATION.md Section 6 endpoint)
  ▼
API (Presentation layer)
  │  authenticates (Section 13), maps request → Use Case input, nothing else
  ▼
Use Case (Application layer, Section 4)
  │  orchestrates: ownership check → Domain logic → Repository → Domain Events
  ▼
Domain Services (Section 5) / Domain entities
  │  enforce invariants (Section 7), compute results — zero I/O of their own
  ▼
Repositories (Section 6)
  │  translate Domain aggregates ↔ persisted rows
  ▼
Database (TRADEOS_DATABASE_DESIGN.md)
  │  the single source of persisted truth
  ▼
Domain Events (Section 8)
  │  published within the same transaction, logged to platform.event_log
  ▼
Response
     the Use Case's result, mapped back to the API's response shape
     (TRADEOS_API_SPECIFICATION.md Section 6) by the Presentation layer —
     the only layer that ever touches an HTTP status code or a JSON envelope shape
```

Every arrow above is one-directional and matches the dependency direction already fixed in Section 2.4 — nothing in this diagram permits a step to call back "up" past the layer that invoked it.

---

## 18. Future Extensibility

Because every module (Section 3) already corresponds 1:1 to a Bounded Context with an explicit Application-layer contract (Section 2), every Future Reserved Domain (`TRADEOS_DOMAIN_MODEL.md` Section 17) attaches additively:

- **AI Coach:** a new module, downstream-only, subscribing to Domain Events (Section 8) and calling Statistics' read-only interface — never gaining write access to Trading, Evaluation, or Configuration's aggregates.
- **Broker Integrations / TradingView Sync:** a new module sitting upstream of Trading, calling `RegisterTrade` (Section 4.1) exactly as a human-triggered request does today — Trading's Use Case does not need to know or care which caller triggered it.
- **Plugin SDK / Public API:** requires the API Key authentication scheme named in Section 13 — a Presentation-layer addition, not a Domain or Application change in any existing module.
- **Multi-User / Teams / Organizations / Workspaces:** conditional on Product Bible Open Question 2. If resolved toward yes, every Repository (Section 6) gains an additional scoping parameter (workspace, not just user) alongside the ownership rule it already enforces (Section 13) — additive to every module uniformly, not a redesign of any single one.

---

## 19. Traceability Matrix

| Business Capability | Backend Module | Use Case | Domain Service | Repository | Database Module | API Endpoint |
|---|---|---|---|---|---|---|
| Register and score a trade | Trading, Evaluation | RegisterTrade | EvaluationEngine | TradeRepository | `trading` | `POST /trades` |
| Close a trade | Trading | CloseTrade | — | TradeRepository | `trading` | `POST /trades/{id}/close` |
| Re-score a trade deliberately | Trading, Evaluation | ReevaluateTrade | EvaluationEngine | TradeRepository, ScoringConfigurationRepository | `trading`, `configuration` | `POST /trades/{id}/reevaluate` |
| Preview a score | Evaluation | PreviewEvaluation | EvaluationEngine | — | *(none)* | `POST /evaluation/preview` |
| Publish scoring rules | Configuration | PublishScoringConfigurationVersion | — | ScoringConfigurationRepository | `configuration` | `POST /configuration/versions/{id}/publish` |
| Tag a mistake | Trading, Configuration | TagMistake | — | TradeRepository, CatalogRepository | `trading`, `configuration` | `POST /trades/{id}/mistakes` |
| Manage reference lists | Configuration | Create/Update/DeactivateCatalogEntry | — | CatalogRepository | `configuration` | `POST/PATCH /catalogs`, `POST /catalogs/{id}/deactivate` |
| Document a setup | Playbook | Create/Update/DeprecatePlaybookSetup | — | PlaybookSetupRepository | `playbook` | `POST/PATCH /playbook-setups/{id}` |
| See setup performance | Playbook, Statistics | GetPlaybookSetup | StatisticsAggregationService | PlaybookSetupRepository, TradeRepository | `playbook` | `GET /playbook-setups/{id}` |
| Rank mistakes | Mistakes | GetMistakeRanking | MistakePriorityRankingService | TradeRepository, CatalogRepository | *(none)* | `GET /mistakes/ranking` |
| Analyze performance | Statistics | GetStatisticsOverview/ByDimension/Rolling | StatisticsAggregationService | TradeRepository | *(none)* | `GET /statistics/*` |
| Reflect qualitatively | Journal | CreateJournalEntry | — | JournalEntryRepository | `journal` | `POST /journal-entries` |
| Authenticate | Identity | Register/Login/Refresh/Logout | — | UserAccountRepository | `identity` | `POST /auth/*` |
| Personalize | Preferences | UpdatePreferences | — | UserPreferencesRepository | `preferences` | `PATCH /preferences` |

Every Use Case in Section 4 appears in, or is a variant of, a row above — matching the same standard already established by `TRADEOS_API_SPECIFICATION.md` Section 19, `TRADEOS_DATABASE_DESIGN.md` Section 15, and `TRADEOS_DOMAIN_MODEL.md` Section 18.

---

## 20. Implementation Readiness Assessment

**Purpose:** an implementation-planning aid only, for sequencing Claude Code's module-by-module build. Every status, dependency, and ordering below is a *reading* of what the seven frozen documents and this blueprint already establish — including the code-state findings already on record in `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 15 (Known Gap: Current Code vs. Target Architecture) and `PROJECT_AUDIT.md`. It introduces no new business rule, architectural decision, database change, or API change.

| Module | Current Status | Blocking Dependencies | Documents Required | Estimated Implementation Order | Notes |
|---|---|---|---|---|---|
| Infrastructure / Platform (§3.12) | **Ready** | None | `TRADEOS_SYSTEM_ARCHITECTURE.md` §2–3, 6; `TRADEOS_DATABASE_DESIGN.md` §6.18; this document §2, 8, 11, 13 | 1 | Foundational — event dispatcher, auth middleware, and `platform.event_log` should exist before any other module is meaningfully testable end-to-end |
| Identity (§3.1) | **Ready** | Infrastructure / Platform | `TRADEOS_DOMAIN_MODEL.md` §8.11; `TRADEOS_DATABASE_DESIGN.md` §6.1; `TRADEOS_API_SPECIFICATION.md` §6.1–6.2; this document §3.1, 4.8, 6.6 | 2 | No design ambiguity remains; the Generic Domain's minimal scope (§3.4 of the Domain Model) keeps this module small |
| Preferences (§3.2) | **Ready** | Identity (1:1 with `UserAccount`) | `TRADEOS_DOMAIN_MODEL.md` §8.12; `TRADEOS_DATABASE_DESIGN.md` §6.2; `TRADEOS_API_SPECIFICATION.md` §6.3 | 3 | Trivial scope; safe to build alongside Identity rather than strictly after it |
| Configuration (§3.5) | **Partial** | Infrastructure / Platform | `TRADEOS_DOMAIN_MODEL.md` §8.4–8.6; `TRADEOS_DATABASE_DESIGN.md` §6.3–6.7, §7; `TRADEOS_API_SPECIFICATION.md` §6.6; this document §3.3, 4.5, 4.9, 6.2 | 4 | Must exist, and be seeded with a default published `ScoringConfigurationVersion`, before Evaluation or Trading can be exercised end-to-end; substantial reference criteria/weight data already exists from the Excel-era design work (`PROJECT_AUDIT.md`), which reduces net-new modeling |
| Catalogs (§3.6) | **Partial** | Configuration (shares the same schema/module family, `TRADEOS_DATABASE_DESIGN.md` §3) | Same as Configuration, plus `TRADEOS_DATABASE_DESIGN.md` §6.8 | 5 | Reference catalog data (Setups, Sessions, Strategies, Entry Triggers, Mistake Tags) already exists from prior design sessions per `PROJECT_AUDIT.md`, easing seeding |
| Evaluation (§3.4) | **Partial** | Configuration | `TRADEOS_DOMAIN_MODEL.md` §8.2, 12.1; `TRADEOS_DATABASE_DESIGN.md` §7; `TRADEOS_API_SPECIFICATION.md` §6.5; this document §3.2, 4.4, 5.1 | 6 | Per `TRADEOS_SYSTEM_ARCHITECTURE.md` §15's own Known Gap, only the Confidence engine is currently wired into the existing reference code — Quality, Execution, Market Context, and Bias remain to be implemented against the same already-designed generic engine pattern, not a new one |
| Trading (§3.3) | **Partial** | Evaluation, Configuration, Catalogs | `TRADEOS_DOMAIN_MODEL.md` §8.1, 8.3; `TRADEOS_DATABASE_DESIGN.md` §6.9–6.14; `TRADEOS_API_SPECIFICATION.md` §6.4; this document §3.1 (Trading entry), 4.1–4.3, 4.6, 6.1 | 7 | Basic Trade CRUD exists in the reference implementation (`TRADEOS_SYSTEM_ARCHITECTURE.md` §15), but full Pro-mode fields, MFE/MAE computed properties, and Mistake tagging are not yet wired |
| Journal (§3.10) | **Planned** | Trading (for trade-scoped entries only — period-scoped entries need no Trade at all) | `TRADEOS_DOMAIN_MODEL.md` §8.10; `TRADEOS_DATABASE_DESIGN.md` §6.17; `TRADEOS_API_SPECIFICATION.md` §6.11 | 8 | Structurally simple; safe to build in parallel with Trading's later stages once the `trades` table exists |
| Mistakes (§3.8) | **Planned** | Trading (`trade_mistakes` junction), Catalogs (`mistake_tag` entries) | `TRADEOS_DOMAIN_MODEL.md` §12.3; `TRADEOS_API_SPECIFICATION.md` §6.9; this document §5.3 | 8 | Pure read-side, no persistence of its own (§3.8) — quick to build once its two dependencies hold real data; safe alongside Journal |
| Statistics (§3.9) | **Planned** | Trading, Evaluation (needs real Trade + Evaluation data to aggregate) | `TRADEOS_DOMAIN_MODEL.md` §12.2; `TRADEOS_API_SPECIFICATION.md` §6.10; this document §5.2 | 9 | Meaningful testing benefits from more than `PROJECT_AUDIT.md`'s currently-confirmed two real historical Trades — functionally buildable earlier, but validating it is more convincing with more data |
| Playbook (§3.7) | **Planned** | Catalogs, Statistics (composed for live performance, never stored) | `TRADEOS_DOMAIN_MODEL.md` §8.8; `TRADEOS_DATABASE_DESIGN.md` §6.15–6.16; `TRADEOS_API_SPECIFICATION.md` §6.8; this document §3.7, 6.4 | 10 | Last of the confirmed modules, since its detail view depends on Statistics already working |
| Reports (§3.11) | **Blocked** | No confirmed Domain Model entity or API module exists | None can be written yet — requires upstream Product Bible/Domain Model/API Specification work first | Not scheduled | Reserved namespace only (`TRADEOS_API_SPECIFICATION.md` API-6) |
| Future AI, Future Notifications (§3.13) | **Blocked** | Same as Reports | Same as Reports | Not scheduled | Reserved namespace only (`TRADEOS_DOMAIN_MODEL.md` §17) |

**How to read "Estimated Implementation Order":** a number, not a date — modules sharing a number (e.g., Journal and Mistakes, both 8) are judged independently buildable in parallel once their listed dependencies are satisfied, not strictly sequential. This ordering reflects dependency structure only (Section 2.4, 3), not effort estimation, which this document does not attempt.

---

## 21. Known Gaps & Open Questions

| ID | Topic | Current State | Target State | Reason | Impact | Priority |
|---|---|---|---|---|---|---|
| BE-1 | Domain Events for Identity actions (register/login) | None named in `TRADEOS_DOMAIN_MODEL.md` Section 11 | A decision on whether auth actions deserve Domain Events (for future security/audit tooling) | Not addressed by any frozen document | Low today; rises if a future security audit requirement appears | Low |
| BE-2 | Domain Event for Trade soft-deletion | None named | A decision on whether deletion deserves its own event, distinct from amendment | Not addressed by any frozen document | Low — deletion is expected to be rare | Low |
| BE-3 | Domain Events for individual Configuration writes (criterion/weight create or edit, short of publish/deactivate) | Only `ScoringConfigurationChanged` (publish) and `CatalogEntryDeactivated` are named | A decision on whether finer-grained events are needed for audit purposes | `TRADEOS_DOMAIN_MODEL.md` Section 11 does not name them | Low — `platform.event_log`'s created/updated timestamps already provide some audit trail even without a named event | Low |
| BE-4 | `PlaybookRecommendationService` has no confirmed endpoint | The service is named (`TRADEOS_DOMAIN_MODEL.md` Section 12.4) but no API endpoint surfaces its output | An endpoint (or a field on the Playbook Setup response) exposing its suggestions | Not specified in `TRADEOS_API_SPECIFICATION.md` | Medium — a designed capability with no way to reach it yet | Medium |
| BE-5 | Concurrency/isolation strategy for concurrent edits to the same aggregate | Not specified — assumed non-issue at single-user scale | A defined isolation level and conflict resolution (e.g., optimistic locking via a version column) | No frozen document addresses this | Low today; rises immediately if multi-user or multi-tab editing becomes real | Medium |
| BE-6 | Concurrent "publish" race on the same draft Configuration version | Not specified | A defined locking or compare-and-swap strategy for the publish action specifically | Same root cause as BE-5, called out separately since this specific action is unusually consequential | Low — requires two near-simultaneous publish attempts, unlikely for a single user | Low |
| BE-7 | Health check endpoint | Assumed necessary by this document (Section 11) but not named in `TRADEOS_API_SPECIFICATION.md` | Add a `/healthz`-style endpoint to that document in a future revision | This document should not silently introduce a new confirmed endpoint on its own authority | Low | Low |
| BE-8 | "Reports" module | Reserved namespace only (Section 3.11) | Full module design once a Domain Model entity exists | Consistent with `TRADEOS_API_SPECIFICATION.md` API-6 and `TRADEOS_DATABASE_DESIGN.md`'s equivalent gap | Low | Low |
| BE-9 | Background job technology | Not chosen — this document is deliberately technology-agnostic (Section 10) | A specific choice, made only once a real background job (Section 10) is being built | Premature to decide before a real need exists, per Architectural Principle 4 | Low today | Low |
| BE-10 | **Bulk re-evaluation of historical Trades** | `TRADEOS_DOMAIN_MODEL.md` Section 8.2 explicitly names "any explicit 'recalculate historical trades' action" as a real, anticipated capability, distinct from a single Trade's re-evaluation. No document among the seven frozen ones — not the API Specification, not the Frontend Blueprint, not this one until now — actually defines it. Only a **per-Trade** `POST /trades/{id}/reevaluate` (`TRADEOS_API_SPECIFICATION.md` Section 6.4) exists anywhere | Either confirm re-evaluation is always meant to be per-Trade only (and the Domain Model's phrase was describing that same per-Trade action, not a distinct bulk one), or design a real bulk/background use case (Section 10) | This is a genuine gap discovered by tracing one specific Domain Model sentence through every downstream document and finding it was never actually built — not silently resolved here, per this document's explicit instruction on cross-document inconsistencies | **The most consequential gap in this document:** a trader who publishes a new Configuration version today has no way to re-score more than one historical Trade at a time, which may not match what "recalculate historical trades" was meant to promise | Medium-High |

---

## 22. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial Backend Blueprint. Derived from all seven frozen foundational documents. Applied `TRADEOS_SYSTEM_ARCHITECTURE.md`'s already-decided Modular Monolith and Clean Architecture one level deeper: 13 backend modules, 7 Use Cases in full detail plus 12 compact, 4 Domain Services, 7 Repositories, a 6-layer Validation Blueprint, all 8 Domain Events with their dispatch contract, transaction/background-processing/logging/error-handling/security/performance/testing blueprints, folder organization, a component interaction diagram, future extensibility, a full traceability matrix, and ten registered Open Questions (BE-1 through BE-10) rather than invented answers — including BE-10, a genuinely consequential gap found by tracing the Domain Model's "recalculate historical trades" phrase through every downstream document and confirming it was never actually designed as a bulk capability, only ever as the existing per-Trade action. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Added Implementation Readiness Assessment (Section 20) — a per-module Status/Blocking Dependencies/Documents Required/Estimated Order/Notes matrix for Claude Code's implementation sequencing, introducing no new business rule, architectural decision, database change, or API change. Renumbered Known Gaps (→ Section 21) and Document Control (→ Section 22) accordingly, and re-verified every internal cross-reference, the Traceability Matrix, and the Open Questions registry against the new numbering — no additional inconsistencies found. |

**Status:** FROZEN. This is the eighth permanent foundational document of TradeOS, after `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`, `TRADEOS_API_SPECIFICATION.md`, and `TRADEOS_FRONTEND_BLUEPRINT.md`. The Backend Blueprint is complete and implementation-ready.
**Next document:** to be determined.
