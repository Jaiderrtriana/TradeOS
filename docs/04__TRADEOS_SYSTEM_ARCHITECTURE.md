# TRADEOS_SYSTEM_ARCHITECTURE.md

**Document Status:** CANONICAL AND FROZEN — the permanent system architecture of TradeOS.
**Version:** 1.3
**Last Updated:** 2026-08-07
**Depends On:** `TRADEOS_PRODUCT_BIBLE.md` v2.1 (frozen) and `TRADEOS_DOMAIN_MODEL.md` v1.1 (frozen). This document does not re-litigate any business or domain decision made in those two — it defines how the domain described in the Domain Model is realized as a running system.
**Relationship to `TRADEOS_MASTER_ROADMAP.md`:** the Roadmap remains canonical for *sequencing* (versions, milestones, order of work). Where the Roadmap's architecture and technology sections (its Sections 2 and 12) overlap with this document, **this document now wins** — the Roadmap should be treated as historically informative on those points, not authoritative, and revised to reference this document rather than restate it.
**Does Not Cover:** database schemas, tables, or storage-level design (the next document); API endpoint paths or request/response contracts; UI layout.

---

## 0. Purpose and Scope

The Domain Model (`TRADEOS_DOMAIN_MODEL.md`) defines *what* TradeOS's business domain is — its Bounded Contexts, aggregates, and rules — independent of any technology. This document defines *how* that domain is realized as software that actually runs: what architectural style holds it together, how its Bounded Contexts are packaged and deployed, how they talk to each other, what technology each piece uses, and how the system behaves under growth, attack, and failure.

Every architectural decision below must be traceable to a Bounded Context, Domain Service, or Non-Functional Requirement already named in the two frozen documents. Where this document introduces something genuinely new (a technology choice, a communication pattern), it says so explicitly rather than presenting it as if it were already decided elsewhere.

This document distinguishes two kinds of decision, and that distinction governs how the rest of it should be read:

- **Business architecture** — module boundaries, Bounded Context interactions, communication patterns, event flow, quality attribute priorities. These are direct, structural consequences of the frozen Domain Model and Product Bible. Changing them requires the same rigor as changing those documents.
- **Technology/implementation decisions** — specific languages, frameworks, databases, hosting platforms (Section 8). These are choices made *in service of* the business architecture, not part of it. See Section 8.4 for how they may evolve independently, without reopening this document.

---

## 1. Architectural Principles

These are engineering-level principles — distinct from, and narrower than, the product-level Principles in `TRADEOS_PRODUCT_BIBLE.md` Section 7. Every architectural decision in this document, and every future one, must be checked against this list.

1. **Domain Independence.** The Domain layer of any module never depends on infrastructure, a framework, or a specific technology. It is pure business logic, testable with nothing but a test runner (Section 2.1). This is what already lets `test_evaluation_engine.py` run without a database.
2. **Module Boundaries Are Contracts, Not Suggestions.** A module's public interface is the only way another module may interact with it — enforced in code structure (Section 3.3 forbidden dependencies), not merely documented as a convention to be trusted.
3. **Explicit Over Implicit.** State changes are visible, named events or direct calls — never hidden side effects. A `Trade` amendment is an explicit `TradeAmended` event, never a silent overwrite (Domain Model DI-01). A configuration change never implicitly rewrites history (Domain Model DI-07).
4. **Simplicity Until Proven Insufficient.** No microservice, message broker, cache, or distributed system is introduced until a real, demonstrated need exists — not in anticipation of one. Every "not built now" decision in this document (Sections 6.3, 10, 13) follows from this principle, which is itself the architectural expression of Product Bible Principle 3 (Every Feature Must Earn Its Place).
5. **Observability Is Not Optional.** The system must never fail silently (Product Bible NFR 10.6). Every module that can fail must fail loudly — a visible error or a logged exception — never a plausible-looking wrong value. This is the single most important lesson carried forward from the Excel's own history (`PROJECT_AUDIT.md`, Section 3.4).
6. **Prefer Reversible Decisions.** Where two designs satisfy the same requirement, the one that is cheaper to undo or evolve later is preferred. The Modular Monolith (Section 2.2) is chosen partly because it does not foreclose microservices later (Section 10.3); the in-process event dispatcher (Section 6) does not foreclose an async bus later (Section 6.2).
7. **Technology Serves the Domain, Never the Reverse.** No technology choice (Section 8) may require a change to the Domain Model or the business architecture (Sections 2–7, 9–13) to accommodate it. If a technology choice ever seems to require such a change, the technology choice is wrong, not the domain.
8. **Every Decision Is Traceable.** Consistent with the Domain Model's own standard (`TRADEOS_DOMAIN_MODEL.md` Section 1): an architectural decision with no traceable link to a Bounded Context, a Non-Functional Requirement, or one of these Principles should not be made — see Section 14 for the registry that enforces this in practice.

---

## 2. Overall Architectural Style

TradeOS uses two architectural styles at two different levels of granularity, and it is important they are not confused with each other.

### 2.1 At the Code Level: Clean Architecture (Ports & Adapters)

Within any single module, code is organized into four layers, strictly dependent in one direction only (outer depends on inner, never the reverse):

```
Presentation  →  Application  →  Domain  ←  Infrastructure
   (API)          (use cases)   (entities,      (database,
                                 rules, no        external
                                 tech deps)       services)
```

This is not a new decision — it is confirmed as already in place in the reference implementation (`tradeos-backend`'s `app/domain`, `app/application`, `app/infrastructure`, `app/presentation` packages) and is retained as the mandatory style for all future code. The Domain layer's independence is what allows the Domain Model's rules (e.g., `EvaluationEngine`, Domain Model Section 12) to be tested without a database, exactly as `test_evaluation_engine.py` already does. This is the direct application of Architectural Principle 1.

### 2.2 At the System Level: Modular Monolith

TradeOS is deployed as **one single backend service**, internally organized into modules that mirror the Domain Model's Bounded Contexts (Section 3) — not as separate microservices communicating over a network.

**Why not microservices:** microservices are justified by independent scaling needs, independent team ownership, or independent deployment cadence across genuinely large systems. None of these apply today: there is one user (Product Bible Section 4.2), one deployable makes operational sense at current scale (Product Bible NFR 10.4, Availability), and splitting into services now would violate Architectural Principle 4 — the complexity of distributed systems (network calls, partial failure, eventual consistency between services) would be paid for with no corresponding benefit.

**Why "modular" and not just "a monolith":** the Modularity Principle (Product Bible Principle 13; Domain Model Section 4) is enforced by module boundaries *within* the single deployable, not by network boundaries between services. Each Bounded Context is its own top-level code module with its own domain/application/infrastructure/presentation layers, and modules communicate only through each other's public application-layer interface (Section 4) — never by reaching into another module's database tables or domain internals directly (Architectural Principle 2). This is what allows any single module to be extracted into its own deployable service later (Section 10) without redesigning the domain (Architectural Principle 6).

---

## 3. Module Boundaries

Each Bounded Context from the Domain Model becomes exactly one top-level module in the codebase:

| Module | Domain Model Bounded Context |
|---|---|
| `trading` | Trading Context |
| `evaluation` | Evaluation Context (Core Domain) |
| `configuration` | Configuration Context |
| `playbook` | Playbook Context |
| `analytics` | Analytics Context |
| `mistakes` | Mistake Tracking Context |
| `journal` | Journal Context |
| `identity` | Identity & Access Context (Generic) |
| `preferences` | Preferences Context (Generic) |

### 3.1 Analytics Has No Infrastructure Layer of Its Own

Consistent with Domain Model KDD-04 (Analytics owns no data of its own), the `analytics` module has no persistence beyond, at most, an optional performance cache that is never authoritative. Its "infrastructure" is read-only query access into `trading` and `evaluation`'s data, through the contracts those modules expose — it never gains its own tables in the future database design.

### 3.2 Shared Kernel

A small `shared_kernel` holds the handful of Value Objects and Enums used across module boundaries by design (Domain Model Sections 9–10: `Money`, `RMultiple`, `Score`, `Grade`, `Direction`, `TradeResult`, `EngineType`). This is the one deliberate exception to "modules communicate only through contracts" — these types are so foundational that duplicating them per-module would violate the Domain Model's Ubiquitous Language faster than sharing them violates modularity. No entity, aggregate, or domain service is ever part of the shared kernel — only these small, stable value shapes.

### 3.3 Forbidden Dependencies

A module may depend on another module's published contract (Section 4). A module may **never**:
- Import another module's `domain` or `infrastructure` layer directly.
- Query another module's database tables directly (once the database design exists) — always through that module's own repository/service interface.
- Assume another module's internal implementation details (e.g., `analytics` must never assume how `trading` stores a Trade — only that it can ask for one).

This is the literal enforcement mechanism for Architectural Principle 2.

---

## 4. Bounded Context Interactions

This translates the Domain Model's Context Map (`TRADEOS_DOMAIN_MODEL.md` Section 5) into concrete interaction terms.

- **Configuration → Evaluation:** Evaluation's application layer calls Configuration's application layer synchronously to fetch the currently-active `ScoringConfiguration` (or a specified historical version) before computing a Score. Configuration never calls Evaluation.
- **Trading → Evaluation:** when a Trade is registered or reaches a point requiring evaluation, Trading's application layer invokes Evaluation's application layer synchronously, passing the `ChecklistSnapshot` and Trade facts, and receives an `EvaluationSnapshot` back to attach to the Trade — realized as a single in-process call within the same transaction (Section 5), not a fire-and-forget event, because the Trade aggregate is not considered fully saved until its snapshot exists (Domain Model Section 8.1).
- **Analytics → Trading, Evaluation:** read-only queries only. Analytics never calls into Trading's or Evaluation's write paths, and never persists its own copy of their data (Domain Model KDD-04).
- **Playbook → Analytics:** Playbook's read-side performance view calls Analytics' `StatisticsAggregationService` (Domain Model Section 12.2) rather than computing performance itself — the direct architectural enforcement of "reuse, don't duplicate" that the Excel's own Playbook sheet already modeled correctly (referencing `Stats por Set Up`, never recalculating independently).
- **Trading → Mistake Tracking, Journal:** by reference only. A Trade stores a reference (ID) to tagged Mistakes and linked Journal Entries; Mistake Tracking and Journal never write to a Trade.
- **Identity & Access, Preferences:** no interaction with the trading domain graph at all (Domain Model Sections 4.8–4.9) — these modules are called directly by the Presentation layer where needed (e.g., to check authentication before any request reaches a domain module) but are not part of the domain's own call graph.

---

## 5. Internal Communication Patterns

Given the Modular Monolith style (Section 2.2), the primary communication pattern is **direct, synchronous, in-process calls through a module's public application-layer interface** — normal function/method calls, not network requests, not message queues, for anything happening within one user's request.

Two exceptions, both deliberate:

1. **Domain Events are dispatched, not called directly** (Section 6) — a module that changes state publishes an event; interested modules subscribe to it. This decouples "something happened" from "who needs to know," even though today the dispatch mechanism itself is in-process.
2. **Read-heavy, cross-cutting queries (Analytics) go through a dedicated read interface**, not through Trading's or Evaluation's write-side application services — this keeps Analytics' access pattern architecturally distinct from a context's own internal use cases, even though, again, no network boundary separates them today.

**Why this matters for the future:** because every cross-module interaction already goes through a well-defined interface rather than direct object/database access, extracting any one module into its own deployable service later (Section 10) is a matter of replacing an in-process function call with a network call behind the same interface — not a redesign of who calls whom (Architectural Principle 6).

---

## 6. Event Flow

The Domain Model (Section 11) already names the Business Events (`TradeRegistered`, `TradeEvaluated`, `TradeClosed`, `TradeAmended`, `MistakeTagged`, `ScoringConfigurationChanged`, `PlaybookSetupUpdated`, `CatalogEntryDeactivated`). This section defines how they actually flow through the running system today, and how that can evolve.

### 6.1 Today: In-Process, Synchronous Dispatch
An event is published by the module whose action caused it, immediately after that action completes within the same request and the same database transaction. Any subscribing module's handler runs synchronously, in the same request. This is the simplest correct implementation for a single-user, request/response system, and it guarantees an event is never "lost" between being published and being handled, because both happen inside one atomic unit of work.

### 6.2 Future: Asynchronous Event Bus (Not Built Now, Architected For)
If a Future Reserved Domain (Domain Model Section 17) that reacts to events but does not need to block the original request comes online — the clearest example is the **AI Coaching Domain**, which should observe `TradeEvaluated` or `TradeClosed` events to update its own context without making the trader wait — the dispatch mechanism can be swapped for an asynchronous message bus **without changing what events exist, what data they carry, or which modules publish them.** This is possible specifically because Domain Events are already modeled as immutable data (Domain Model Section 11), not as method calls — the publishing module never needs to know whether a subscriber is in-process or on a queue.

### 6.3 Explicit Non-Goal for Now
No message broker (e.g., a pub/sub system) is deployed as part of the current architecture. Introducing one before a real subscriber needs it would violate Architectural Principle 4 in exactly the same way premature microservices would (Section 2.2).

---

## 7. Service Responsibilities

This maps the Domain Model's Domain Services (Section 12 there) to concrete architectural responsibilities, and adds the infrastructure-level services required to support them.

| Service | Layer | Responsibility |
|---|---|---|
| `EvaluationEngine` | Domain (Evaluation module) | Pure function: `(ChecklistSnapshot/Trade facts, ScoringConfiguration, ScoringProfile) → EvaluationSnapshot`. No I/O, no side effects, trivially unit-testable. |
| `StatisticsAggregationService` | Domain/Application (Analytics module) | Given a set of Trades (all-time or a window) and an optional grouping dimension, computes Win Rate, Expectancy, Profit Factor, Average R, and related metrics. Written once, generically (Domain Model KDD-04). |
| `MistakePriorityRankingService` | Domain (Mistake Tracking module) | Given Trades referencing each `MistakeTag`, computes frequency, cost, and priority ranking. |
| `PlaybookRecommendationService` | Domain (Playbook module) | Given `StatisticsAggregationService` output grouped by setup, surfaces promotion/de-emphasis candidates — output only, never writes to `PlaybookSetup` automatically. |
| `TradeRepository`, `ScoringConfigurationRepository`, etc. (one per aggregate root) | Infrastructure (each owning module) | Translate between the Domain layer's aggregates and persisted storage. Never shared across modules — Trading's repository is not accessible from Analytics (Section 3). |
| Authentication service | Infrastructure (Identity & Access module) | Verifies who is making a request. Called by the Presentation layer before a request reaches any domain module — see Section 11. |

---

## 8. Technology Decisions

**These are implementation decisions, not business architecture.** Per the distinction drawn in Section 0, everything in this section may evolve independently of Sections 1–7 and 9–13, provided the replacement technology can still satisfy the same module boundaries, communication patterns, and quality attribute priorities (Section 9). Changing the backend framework, for instance, does not require re-approving this document as a whole — it requires confirming the replacement still honors Architectural Principle 7 (Technology Serves the Domain, Never the Reverse).

| Layer | Decision | Why |
|---|---|---|
| **Backend language/framework** | Python + FastAPI | Already the reference implementation's choice; async-capable; the same language needed for the future Intelligence/Pattern Discovery and AI Coaching domains (Domain Model Section 17), avoiding a language switch when those are built. |
| **Database** | PostgreSQL | Confirmed appropriate for the Domain Model's needs: strong support for the window-function-style queries Analytics requires (Domain Model KDD-04), JSONB for flexible fields (e.g., `EvaluationSnapshot`'s criterion breakdown, Domain Model Section 8.2) without sacrificing relational integrity for Catalog references (Domain Model DI-09). |
| **Frontend** | React + TypeScript | The approved production technology, decided independently of `TradeOS_UI_v3` (see Section 8.5 — that prototype is plain HTML/CSS/JS with no build step, `PROJECT_AUDIT.md` Section 2, and is a UX/navigation/IA reference only, never an implementation baseline). Typed contracts with the backend reduce an entire class of integration bugs the Excel's own history (`PROJECT_AUDIT.md`) shows are otherwise easy to introduce silently. |
| **API style** | REST (JSON over HTTP) | Sufficient for a modular monolith with one client; no current requirement (real-time push, multiple heterogeneous clients) justifies GraphQL or gRPC yet. Revisit only if a Future Reserved Domain (e.g., a mobile client) creates a concrete need. |
| **Authentication** | Token-based (e.g., JWT), issued by the Identity & Access module | Standard, well-understood pattern for the Generic Identity & Access Context (Domain Model Section 3.3) — deliberately not a bespoke design, consistent with "Generic domains get the least design effort" (Domain Model Section 3.4). |
| **Domain Event dispatch** | In-process synchronous dispatcher (Section 6.1) | See Section 6 — no broker until a real asynchronous subscriber exists. |
| **Testing** | pytest (backend), with the Evaluation module held to the highest coverage bar of any module | Directly required by Architectural Principle 5 and by this being the Core Domain (Domain Model Section 3.1). |

### 8.4 How Technology Decisions May Change

A technology decision in this table may be revised via a lightweight process that does **not** require re-freezing this document:

1. State which quality attribute (Section 9) or which Architectural Principle (Section 1) motivates the change.
2. Confirm the replacement technology can still honor every module boundary (Section 3) and communication pattern (Sections 4–5) already established — the replacement must fit the architecture, not reshape it.
3. Record the change in this table and in Section 14 (a new ADR entry) with the date and reasoning.

This is what "technology decisions may evolve independently of the business architecture" means in practice — a framework or database migration is a Section 8 update, not a Section 1–7/9–13 renegotiation.

### 8.5 Prototype Implementation Technology vs. Production Implementation Technology (Correction)

**This subsection corrects a documentation inaccuracy identified after this document's v1.1 freeze — it does not change the technology decision itself.**

`TradeOS_UI_v3` — the 21-page frontend prototype inspected in `PROJECT_AUDIT.md` Section 2 — is a **static HTML/CSS/JS asset set with no build step**, not a React application. v1.1 of this document's Technology Decisions table (Section 8) and Deployment Architecture (Section 12.1) both stated that React + TypeScript was chosen because it was "already the reference prototype's direction." That justification was factually incorrect: the prototype's own implementation technology is vanilla JS, confirmed by direct inspection.

To prevent this ambiguity from recurring, this document now explicitly distinguishes two different things that a "frontend technology" statement could mean, and states each independently:

- **Prototype implementation technology:** plain HTML/CSS/JavaScript, no build tooling, no component framework. This is what `TradeOS_UI_v3` is, and it was built and remains useful **only** as a UX, navigation, and information-architecture reference (`TRADEOS_FRONTEND_BLUEPRINT.md` front matter already states this correctly: "The prototype is a visual reference for feel, never a source of business truth"). It was never intended to become, and is not, the production implementation baseline.
- **Production implementation technology:** React + TypeScript, per Section 8's table. This is, and remains, the approved technology for the production frontend. The decision does not derive from, and was never conditional on, what the prototype happened to be built with — it is justified on its own merits (typed contracts with the backend, per Section 8's table) exactly as every other row in that table is.

**Consequence of this correction:** none to the business architecture (Sections 1–7, 9–13) or to the technology decision itself (Section 8's table, React + TypeScript, is unchanged). The only change is that the *reasoning* no longer cites a prototype-continuity claim that does not hold. Building the production frontend in React + TypeScript is, and always was, a rewrite of `TradeOS_UI_v3`'s validated UX onto a new technical foundation — not a migration or continuation of its existing code — and this was already implicitly true even under the v1.1 wording; it is simply now stated accurately.

---

## 9. Quality Attributes Matrix

Every architectural decision above serves some combination of these attributes. They are listed here in **priority order** — when two attributes conflict, the one listed first wins, unless a specific documented exception says otherwise. This ordering is itself an architectural decision, grounded in Product Bible Section 10 (Non-Functional Requirements) and in this project's own history.

| Priority | Attribute | Why This Priority | Primarily Served By |
|---|---|---|---|
| 1 | **Correctness** | The Evaluation Engine's entire purpose is to produce a trustworthy score (Product Bible Principle 10, Transparency Builds Trust). The Excel's own history (`PROJECT_AUDIT.md`) shows silent correctness failures are this project's single most expensive recurring defect class. Nothing outranks this. | Domain Independence (Principle 1), the Evaluation module's mandatory test coverage bar (Section 8), Domain Invariants (Domain Model Section 14) |
| 2 | **Reliability** | A close second to correctness for the same historical reason: a system that fails loudly and recovers is far preferable to one that quietly returns a plausible wrong answer. | Observability Is Not Optional (Principle 5), same-transaction Trade/Evaluation writes (Section 4) |
| 3 | **Maintainability** | TradeOS is currently maintained by one person (Product Bible Section 4.2). A system that cannot be understood and safely changed by one person fails regardless of any other quality. | Module Boundaries Are Contracts (Principle 2), Clean Architecture (Section 2.1), package-by-module structure (Section 3) |
| 4 | **Extensibility** | The Domain Model and Product Bible both explicitly design for growth (a sixth Evaluation engine, Future Reserved Domains) — the architecture must not need to be rebuilt to accommodate what is already anticipated. | Config-driven Evaluation Engine (Domain Model Section 8.2), event-based extension seams (Section 6.2), Future Reserved Domains (Domain Model Section 17) |
| 5 | **Security** | Real and non-negotiable at the baseline level (transport encryption, authenticated boundaries — Section 11.1), but its *deepest* posture is explicitly deferred pending Product Bible Open Question 3 — it is prioritized above Performance and Scalability precisely because a single-user system's data is still sensitive, but ranked below the first four because the current scope does not yet demand a fully elaborated security program. | Baseline security architecture (Section 11.1) |
| 6 | **Performance** | Must feel instantaneous for the core loop (logging a trade, checking a checklist — Product Bible NFR 10.1) but analytical queries are explicitly permitted to be slower than instant, provided they remain usable in the moment. | Stateless application layer (Section 10.1), Trading/Evaluation's single-Trade operation cost (Section 10.1) |
| 7 | **Scalability** | A real, named target (20,000+ trades, Product Bible NFR 10.2) — but with no current urgency, because there is exactly one user today. Ranked last because designing for scale the system does not yet need, ahead of the six attributes above, would itself violate Architectural Principle 4. | Stateless application layer, module extraction path (Section 10.3), deferred caching for Analytics (Section 10.1) |

**How to use this matrix:** when a design decision must trade one attribute against another (for example, a caching layer that would improve Performance at the cost of Correctness risk, per Domain Invariant DI-11), the higher-priority attribute wins by default. Overriding this order for a specific decision requires stating so explicitly, as an exception, in the relevant section or in a new ADR (Section 14) — never silently.

---

## 10. Scalability Strategy

Grounded in Product Bible NFR 10.1 (Performance) and 10.2 (Scalability: 20,000+ trades), and in the priority order established in Section 9.

### 10.1 Within the Modular Monolith
- **Database indexing** on the fields Analytics and Rolling Statistics query most (Trade's timestamp, Strategy/Setup/Session/Direction references) is an architectural requirement carried into the database design document, not solved here — but the *principle* that Analytics' query patterns must drive indexing decisions (not be an afterthought) is established now, precisely because the Excel's own performance problems (`PROJECT_AUDIT.md`, Section 3.4) came from exactly this kind of oversight.
- **Analytics remains computed-on-demand** (Domain Model KDD-04) rather than cached by default; if a specific query proves too slow at real volume, an explicit, tracked caching layer may be introduced — but only after being demonstrated necessary, never pre-emptively (Architectural Principle 4).
- **Stateless application layer:** the backend holds no in-memory session state between requests, so multiple instances of the same backend can run behind a load balancer without coordination, if and when that is needed.

### 10.2 Path to Horizontal Scaling (Conditional)
If Product Bible Open Question 2 (business model) resolves toward offering TradeOS to other traders, the Modular Monolith already supports the standard next steps without a domain redesign: multiple stateless backend instances behind a load balancer, read replicas of the database for Analytics' read-heavy queries, and — only if a specific module's load genuinely outpaces the rest — extracting that one module into its own deployable service, using the same public-interface boundary already enforced internally (Sections 4–5). This path is explicitly **not being built now**; it is confirmed possible without contradicting anything already decided.

### 10.3 Path to Distributed Extraction (Conditional, Longer-Term)
Because module boundaries already correspond to Bounded Contexts and already communicate only through defined interfaces (Sections 4–5), the single module most likely to be extracted first — if it ever needs to be — is Evaluation (Core Domain, likely to gain the most computational complexity from future Pattern Discovery/AI work) or Analytics (most likely to become read-heavy at scale). Neither extraction is planned; both are architecturally unblocked.

---

## 11. Security Architecture

Grounded in Product Bible NFR 10.3, which explicitly leaves the *detailed* security posture as Open Question 3, and in Section 9's priority ranking (Security above Performance/Scalability, below Correctness/Reliability/Maintainability/Extensibility). This section states the baseline architecture that holds regardless of how that question resolves, and flags what remains genuinely open.

### 11.1 Established Now
- **Transport encryption:** all traffic between client and backend uses TLS. Not optional, not deferred.
- **Authentication at the boundary:** every request to a module other than public health checks passes through the Identity & Access module's verification before reaching any domain module (Section 7) — no module implements its own ad hoc authentication.
- **Secrets management:** database credentials, signing keys, and any third-party API keys are never committed to source control and are injected via environment configuration — a baseline practice, not a differentiator.
- **Least-privilege data access:** a module's infrastructure layer (its repositories) is the only code path permitted to reach the database tables belonging to its own Bounded Context (Section 3) — this is an application-level enforcement of least privilege, independent of and in addition to whatever database-level permissions the next document defines.

### 11.2 Explicitly Still Open (Product Bible Open Question 3 — Not Answered Here)
- Whether TradeOS staff (if TradeOS ever has staff) can access user data, and under what conditions.
- Formal breach response process.
- Any compliance regime (GDPR/CCPA or otherwise) — relevant only if Open Question 2 resolves toward multi-user, per Product Bible Section 10.3.

This document does not invent answers to the above. It confirms that nothing in Section 11.1's baseline is incompatible with any future answer to them.

**Encryption at rest — resolved, Sprint 9.3 (`CHANGELOG.md`):** the managed hosting platform (Render) provides disk-level encryption at rest (AES-256, covering primary, replica, and backup Postgres instances), verified against [render.com/docs/databases](https://render.com/docs/databases). This resolves Master Plan OQ-4 and the encryption-standard component of the Open Question above; the remaining components (staff access, breach response, compliance) stay listed above, unresolved, exactly as before.

---

## 12. Deployment Architecture

Grounded in Product Bible NFR 10.4 (Availability: "modest for a single-user system") and the Modular Monolith style (Section 2.2).

### 12.1 Current Target
- **Backend:** one containerized deployable (the Modular Monolith), running all modules in a single process.
- **Database:** a managed PostgreSQL instance — not self-administered, to avoid spending effort on database operations that don't differentiate the product (Architectural Principle 4).
- **Frontend:** static hosting for the React/TypeScript build, served independently of the backend. (`TradeOS_UI_v3` is also, today, served as a static asset set — but as a plain HTML/CSS/JS prototype, not a React build; see Section 8.5. The similarity is only in hosting shape, not in implementation technology.)
- **Hosting platform:** a simple managed platform (the class of service `TRADEOS_MASTER_ROADMAP.md` already pointed to — Railway/Fly.io/Render-equivalent) rather than self-managed cloud infrastructure (AWS/GCP raw compute) — appropriate to current scale and explicitly revisited only if Open Questions 1/2 resolve toward something that needs it. **Render was selected as the specific vendor within this class in Sprint 9.2** (`CHANGELOG.md`; deployment configuration in `render.yaml`) — the class-level commitment above is preserved rather than rewritten, since the underlying architectural decision (containerized backend, managed Postgres, independently-hosted static frontend) does not change if the vendor ever does. As of Sprint 9.2, `render.yaml` is complete and locally verified but has not yet been applied against a live Render account — see `CHANGELOG.md`, Sprint 9.2, for exactly what remains a manual step.

### 12.2 Explicitly Conditional
Everything in 12.1 is sized for "one user, personal use, no fixed uptime guarantee beyond not losing data." If Product Bible Open Question 2 resolves toward offering TradeOS to others, deployment architecture is the first document that must be explicitly revisited — not silently stretched to cover a scenario it wasn't sized for (this mirrors the same caution already stated in Product Bible NFR 10.4).

---

## 13. External Integrations

As of this document, **TradeOS has zero external integrations in its current architecture.** This is deliberate, not an oversight:

- **Broker/Exchange Integration** is a Future Reserved Domain (Domain Model Section 17), explicitly modeled as sitting *upstream* of the Trading Context (supplying data that triggers `TradeRegistered`) rather than being built into Trading Context itself — so that when it is built, it plugs into an existing seam rather than requiring Trading to be reopened.
- **AI Coaching** (Future Reserved Domain) will, when built, be the first genuine external-service integration (a Large Language Model provider) — architected in Section 6.2 as a downstream, event-driven consumer, never a dependency the core trading flow requires to function.
- **No real-time market data integration** exists or is planned for the current scope (Product Bible Section 11, Out of Scope).

---

## 14. Architecture Decision Records

A consolidated, scannable registry of every major decision already reasoned through inline above. Format matches the Domain Model's Key Domain Decisions (`TRADEOS_DOMAIN_MODEL.md` Section 6) for cross-document consistency.

### ADR-01: Modular Monolith, not microservices
**Context:** the system could be built as independently deployed services from the start.
**Decision:** one deployable, internally modularized by Bounded Context.
**Alternatives considered:** microservices per Bounded Context.
**Reasoning:** Product Bible Open Questions 1/2 unresolved; one confirmed user today; distributed-systems complexity has no current justification (Section 2.2; Architectural Principle 4).
**Consequences:** simpler operations now; a documented, unblocked extraction path later (Section 10.3).

### ADR-02: Package by Bounded Context, layered within (not layer-first)
**Context:** the existing reference implementation organizes code by technical layer first, module second.
**Decision:** reorganize to module-first, layer-second (Section 3).
**Reasoning:** directly enforces Architectural Principle 2 in the code structure itself, not just in documentation.
**Consequences:** a known, tracked refactor of the existing codebase (Section 15).

### ADR-03: Synchronous, same-transaction Trade↔Evaluation scoring
**Context:** Trade registration and Evaluation scoring could be decoupled asynchronously.
**Decision:** synchronous, same-transaction call (Section 4).
**Reasoning:** Domain Invariant DI-06 requires atomic creation of Trade + EvaluationSnapshot.
**Consequences:** Evaluation must respond within the request; acceptable given Correctness/Reliability outrank Performance (Section 9).

### ADR-04: On-demand Analytics computation, no materialized views in v1
**Context:** Analytics could cache or persist its own aggregates for speed.
**Decision:** always computed fresh from Trading + Evaluation data (Section 4).
**Reasoning:** Domain Invariant DI-11 and Domain Model KDD-04 — Analytics must never risk drifting from source data; this is Correctness (priority 1) outranking Performance (priority 6), per Section 9.
**Consequences:** potential future performance cost at scale, deferred to the database design document (indexing) rather than solved by caching now.

### ADR-05: In-process event dispatcher, no external message broker in v1
**Context:** Domain Events could be published to an external broker (Kafka/RabbitMQ-class system) from the start.
**Decision:** in-process, synchronous dispatch (Section 6.1).
**Reasoning:** matches the Modular Monolith decision; avoids a new silent-failure surface disproportionate to current scale (Architectural Principle 4; Principle 5).
**Consequences:** a documented, unblocked path to an async bus later (Section 6.2), with zero change to event shapes or publishers required.

### ADR-06: PostgreSQL as the single database technology
**Context:** a separate document store was considered for `EvaluationSnapshot`'s flexible, JSON-shaped criterion breakdown.
**Decision:** one PostgreSQL instance for all persisted data (Section 8).
**Reasoning:** JSONB gives the flexibility a document store would offer, without sacrificing the relational integrity Catalog references require (Domain Invariant DI-09) or introducing cross-database consistency risk.
**Consequences:** all future modules persist through the same database technology unless a specific, demonstrated need argues otherwise (Architectural Principle 4).

### ADR-07: Token-based authentication via a Generic Identity & Access module
**Context:** authentication could be built bespoke or deferred entirely for a single-user system.
**Decision:** standard token-based (JWT-class) authentication, present from the start (Section 11.1).
**Reasoning:** Generic Domains get the least *design* effort (Domain Model Section 3.4), which means using a well-understood standard pattern, not skipping the concern — security's baseline (Section 9, priority 5) is non-negotiable even pre-multi-user.
**Consequences:** the security boundary does not need retrofitting later if Open Question 2 resolves toward multi-user.

### ADR-08: Quality attribute priority order (Section 9) is fixed unless explicitly overridden
**Context:** without an explicit order, individual decisions risk silently prioritizing convenience (e.g., Performance) over Correctness on a case-by-case basis.
**Decision:** Correctness > Reliability > Maintainability > Extensibility > Security > Performance > Scalability, as a standing default.
**Reasoning:** directly reflects this project's own history — every costly defect found during the Excel's construction was a Correctness/Reliability failure, never a Performance or Scalability one.
**Consequences:** any future decision that trades a higher-priority attribute for a lower one must say so explicitly, as a documented exception, never implicitly.

---

## 15. Known Gap: Current Code vs. This Target Architecture

Consistent with this project's practice of stating "is" versus "should be" honestly (Domain Model KDD-06) rather than assuming they already match:

- The reference implementation (`tradeos-backend`) currently organizes code by technical layer first, not by module-then-layer (Section 3; ADR-02). This is a structural reorganization to carry out during implementation, not a contradiction requiring this document to change.
- Only the Confidence engine is currently wired into the running code; Quality, Execution, Market Context, and Bias are designed (Domain Model, Product Bible) but not yet present in the deployable. This affects implementation sequencing (governed by `TRADEOS_MASTER_ROADMAP.md`), not this architecture document.
- No Domain Event dispatch mechanism (Section 6.1) exists in code yet — today, effects that a published event would trigger are, where they exist at all, invoked directly. Introducing the dispatcher is a concrete, tracked implementation task.

---

## 16. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial System Architecture. Derived from `TRADEOS_PRODUCT_BIBLE.md` v2.1 and `TRADEOS_DOMAIN_MODEL.md` v1.1. Defined architectural style, module boundaries, bounded context interactions, communication patterns, event flow, service responsibilities, technology decisions, scalability strategy, security architecture baseline, deployment architecture, and external integrations. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Added Architectural Principles (Section 1, engineering-level, distinct from the Product Bible's product-level principles), a Quality Attributes Matrix with explicit priority ordering (Section 9), a consolidated Architecture Decision Records registry (Section 14), and an explicit clarification (Section 0, Section 8) that technology/implementation decisions are distinct from business architecture and may evolve independently via the lightweight process in Section 8.4. Renumbered all sections accordingly. |
| 1.2 | 2026-07-25 | **Documentation correction, not an architectural change.** Section 8's Frontend row and Section 12.1 both incorrectly justified the React + TypeScript decision by claiming it was "already the reference prototype's (`TradeOS_UI_v3`) direction." `PROJECT_AUDIT.md` Section 2 confirms `TradeOS_UI_v3` is plain HTML/CSS/JS with no build step, not React — this justification was factually inaccurate. Added Section 8.5, explicitly distinguishing **prototype implementation technology** (`TradeOS_UI_v3`: HTML/CSS/JS, UX/IA reference only, never an implementation baseline) from **production implementation technology** (React + TypeScript, approved and unchanged). The technology decision itself, and all business architecture in Sections 1–7 and 9–13, are unaffected — only the inaccurate rationale is corrected. |
| 1.3 | 2026-08-07 | Section 12.1: recorded that Render was operationally selected as the specific vendor within the already-approved hosting-platform class (Sprint 9.2) — this note was first added during that sprint's own self-audit but had not yet received its own Document Control entry; corrected retroactively here rather than left unversioned. Section 11.2: resolved Master Plan OQ-4 — encryption at rest is provided by the managed hosting platform (Render, AES-256, verified against official documentation) (Sprint 9.3). Neither change alters any business or domain architecture in Sections 1–10 or 13. |

**Status:** FROZEN. This is the third permanent foundational document of TradeOS, after `TRADEOS_PRODUCT_BIBLE.md` and `TRADEOS_DOMAIN_MODEL.md`.
**Next document per the reconstruction plan:** database design (schemas, tables), to be created only now that this System Architecture is approved.
