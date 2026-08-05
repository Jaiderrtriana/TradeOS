# TRADEOS_DOMAIN_MODEL.md

**Document Status:** CANONICAL AND FROZEN — the permanent business domain model of TradeOS.
**Version:** 2.0
**Last Updated:** 2026-07-30
**Depends On:** `TRADEOS_PRODUCT_BIBLE.md` v2.1 (frozen) — this document takes that one's product intent as given and models the business domain that implements it.
**Does Not Cover:** database schemas, tables, indexes, or storage technology. That is the subject of a separate document to be written after this one, per Section 20.
**Methodology:** Domain-Driven Design (DDD) — strategic design (bounded contexts, core/supporting/generic domain classification) followed by tactical design (aggregates, entities, value objects, domain events, invariants).

---

## 1. How to Use This Document

Every concept below has a name. That name is the **ubiquitous language** of TradeOS (formalized in Section 2) — it must be used identically in conversation, code, API contracts, and UI copy. If a future document needs a concept not named here, that is a signal this document is incomplete and must be revised first, not that the new document should invent its own terminology.

Traceability works in one direction only: this document is derived from `TRADEOS_PRODUCT_BIBLE.md` and the confirmed business logic in `Trading_Journal_v2_0_Stable.xlsx` (per `PROJECT_AUDIT.md`). It is not derived from either `TradeOS_PRODUCT.docx` v1.0's module list or the archived `EVALUATION_ENGINE_SPECIFICATION.docx` — both are superseded, and any resemblance to their terminology is coincidental where it doesn't conflict, and overridden where it does.

---

## 2. Ubiquitous Language / Glossary

This is the official vocabulary of TradeOS. Every future document — technical or otherwise — must use these terms with exactly this meaning.

### 2.1 Trading Concepts

| Term | Definition |
|---|---|
| **Trade** | One discretionary trading decision, from an optional planning stage through entry to (eventually) close. The aggregate root of the Trading Context. |
| **TradeStatus** | *(v2.0)* The lifecycle stage of a Trade, independent of its financial outcome: `Planned`, `Open`, `Closed`. Replaces the pre-v2.0 conflation of lifecycle stage and outcome inside `TradeResult`. Traced to `Trading_Journal_v2_0_Stable.xlsx`'s `📒 Trades`/`📒 Trades simple` sheets, column `Estado` (`No iniciado`/`Activo`/`Cerrado`) — present in both sheets, confirmed by direct inspection of the workbook's own data-validation lists. |
| **Direction** | Whether a Trade is `Long` or `Short`. |
| **TradeResult** | *(redefined, v2.0)* The terminal outcome of a Closed Trade only: `TP`, `SL`, `BE`. `null` for a Trade whose `TradeStatus` is `Planned` or `Open` — a Trade with no result yet is not "open" *as a result*, it simply has none. Traced to the same Excel sheets' `Resultado` column (`TP`/`BE`/`SL`). |
| **R-Multiple** | A trade's outcome expressed as a multiple of its initial risk (1R). Always computed, never stored as an independent fact. |
| **MFE (Maximum Favorable Excursion)** | The furthest a Trade moved in the trader's favor before it closed, expressed in R. |
| **MAE (Maximum Adverse Excursion)** | The furthest a Trade moved against the trader before it closed, expressed in R. |
| **Captured %** | The percentage of MFE actually realized by the trade's exit. Defined only for TP trades. |
| **Potential Left** | The R left on the table — MFE minus what was actually captured, floored at zero downside contribution. |
| **Strategy** | The broad category of approach behind a Trade (a Catalog kind). |
| **Setup** | The specific, named pattern a Trade is based on (a Catalog kind); the subject of the Playbook. |
| **Session** | The trading session (e.g., time-zone-based market window) a Trade occurred in (a Catalog kind). |
| **Entry Trigger** | The specific confirmation that justified entering at that moment (a Catalog kind). |

### 2.2 Evaluation Concepts (Core Domain)

| Term | Definition |
|---|---|
| **Evaluation Engine** | The generic, configuration-driven scoring service. One engine, instantiated five independent times. |
| **Engine** (as in `EngineType`) | One of the five independent scoring instances: `Confidence`, `Quality`, `Execution`, `MarketContext`, `Bias`. |
| **Confidence** | How good a setup looked *before* entry, independent of outcome. |
| **Quality** | Whether a Trade followed the trader's own plan and rules, independent of P&L. |
| **Execution** | How well a Trade was executed tactically, independent of whether it won or lost. |
| **Market Context** | How clear or strong market conditions were, independent of direction. |
| **Bias** | Which direction the evidence points — the only signed Engine. |
| **Score** | An Engine's 0–100 (or signed, for Bias) output for one Trade. |
| **Grade** | A letter (A+/A/B/C/D) derived from a Score — never assigned independently. |
| **NormalizationStrategy** | `Unsigned` (measures strength/clarity) or `Signed` (measures direction) — how a criterion's raw value becomes part of a Score. |
| **ScoringCriterion** | One measurable input to one Engine, identified by a stable ID. |
| **ScoringWeight** | How much one Criterion counts, for one ScoringProfile. |
| **ScoringConfiguration** | The full, versioned set of Criteria and Weights currently governing all five Engines. |
| **ScoringProfile** | `DayTrading`, `SwingTrading`, or `Scalping` — a named weighting context. |
| **EvaluationSnapshot** | The immutable record of what all five Engines scored for one specific Trade. |
| **ChecklistSnapshot** | The pre-trade context capture that supplies raw inputs to the Evaluation Engine. |

### 2.3 Supporting Domain Concepts

| Term | Definition |
|---|---|
| **Catalog** | A named reference list (Setups, Sessions, Strategies, Entry Triggers, Mistake Tags). |
| **CatalogEntry** | One item within a Catalog; deactivatable, never deleted while referenced. |
| **PlaybookSetup** | The living definition of one trading setup, plus its live-computed performance. |
| **Mistake / MistakeTag** | A named category of trading error a Trade can be tagged with. |
| **JournalEntry** | Free-text qualitative reflection, attached to either one Trade or one date range. |
| **Win Rate** | The proportion of closed Trades that resulted in TP. |
| **Expectancy** | The average expected R-multiple per Trade, given historical Win Rate and average win/loss size. |
| **Profit Factor** | Gross profit divided by gross loss, for a given set of Trades. |
| **Rolling Statistics** | Performance metrics computed over a configurable, moving window of the most recent N Trades, compared against all-time performance. |

### 2.4 Generic Domain Concepts

| Term | Definition |
|---|---|
| **UserAccount** | The identity of the person using TradeOS. |
| **UserPreferences** | Theme, language, notification, and display preferences — contains no business logic. |

### 2.5 DDD Terms Used Throughout This Document

| Term | Definition |
|---|---|
| **Bounded Context** | A boundary within which a term has exactly one meaning. |
| **Core Domain** | The part of the business that is the actual competitive differentiator (Evaluation). |
| **Supporting Domain** | Trading-specific but not itself the differentiator (Trading, Playbook, Analytics, Mistake Tracking, Journal). |
| **Generic Domain** | Not trading-specific at all; solved problems (Identity & Access, Preferences). |
| **Aggregate Root** | The only entry point through which its aggregate may be modified; the unit of transactional consistency. |
| **Entity** | Has identity and a lifecycle, but may not be independently addressable outside its aggregate. |
| **Value Object** | Has no identity — interchangeable with any other instance holding the same data. |
| **Domain Event** | An immutable record that something has happened. |
| **Domain Service** | Behavior that doesn't naturally belong to a single entity. |
| **Invariant** | A rule that must always hold true, enforced at the boundary of an aggregate. |

---

## 3. Strategic Design — Domain Classification

DDD distinguishes domains by how much they matter to competitive differentiation and how much bespoke modeling they deserve. Misclassifying this leads to over-engineering generic concerns (auth, settings) or under-engineering the actual differentiator (evaluation).

### 3.1 Core Domain

**Evaluation** — the Evaluation Engine and everything that depends on it. This is explicitly named the "single most important part" of the Product Bible (Section 8) and is where TradeOS's actual differentiation lives. This domain deserves the deepest modeling, the most rigorous invariants, and the most conservative approach to change (Product Bible Principle 10, Transparency Builds Trust; Principle 2, Process Over Outcome).

### 3.2 Supporting Domains

Domains that are specific to trading and necessary for the product, but not themselves the differentiator:

- **Trading** — the trade lifecycle itself (capture, amendment, closure).
- **Playbook** — setup documentation and performance attribution.
- **Analytics** — statistics, rolling statistics, cross-dimension performance.
- **Mistake Tracking** — error taxonomy, frequency, cost, prioritization.
- **Journal** — qualitative review and reflection.

### 3.3 Generic Domains

Domains with no trading-specific meaning — solved problems that should use standard patterns, not bespoke modeling, and should consume the *least* design effort of the three categories:

- **Identity & Access** — who the user is, authentication.
- **Preferences** — theme, language, notifications (the "Settings" module of the Product Bible, Section 9).

### 3.4 Why This Classification Matters

Effort and design rigor should be spent in this order: Core > Supporting > Generic. A future contributor proposing to spend significant design effort on, e.g., a sophisticated Preferences system before the Evaluation domain is fully modeled would be violating this priority — this is the domain-modeling equivalent of Product Bible Principle 3 (Every Feature Must Earn Its Place).

---

## 4. Bounded Contexts

A bounded context is a boundary within which a term has exactly one meaning. Outside it, the same word may mean something else — this is expected and healthy in DDD, not a naming inconsistency to fix.

### 4.1 Trading Context
**Owns:** the trade record itself — what was bought or sold, at what price, when, how much, and what happened.
**Does not own:** how "good" the trade was (that's Evaluation's job) or which Playbook setup it belongs to beyond a reference (Playbook owns the setup's definition and performance).

### 4.2 Evaluation Context
**Owns:** the five scoring engines (Confidence, Quality, Execution, Market Context, Bias), their configuration (criteria, weights, profiles), and the scored result attached to each trade. This is the Core Domain.
**Does not own:** the raw trade data it scores (Trading Context owns that) — Evaluation *reads* trade and checklist data as input and *produces* a scoring result as output.

### 4.3 Configuration Context
**Owns:** the versionable business configuration that drives Evaluation (criteria catalogs, weights, scoring profiles) and the reference catalogs shared across the system (setups, sessions, strategies, entry triggers, mistake tags).
**Relationship to Evaluation Context:** Configuration is *upstream* of Evaluation — Evaluation cannot compute a score without reading current (or historically-versioned) configuration. They are modeled as separate contexts rather than one because configuration has fundamentally different lifecycle and audience characteristics than the act of scoring itself (see Key Domain Decision KDD-03, Section 6).

### 4.4 Playbook Context
**Owns:** setup definitions (entry/exit criteria, ideal conditions, risk rules) and the read-side aggregation of a setup's historical performance.
**Does not own:** the trades themselves (Trading Context owns those) — Playbook performance is a *view* computed from Trading + Evaluation data, attributed by setup reference.

### 4.5 Analytics Context
**Owns:** the read-side computation of performance metrics (Win Rate, Expectancy, Profit Factor, Average R, etc.) across any dimension (strategy, setup, session, time, direction) and across any window (all-time or rolling).
**Does not own:** any data of its own — Analytics is purely a computation layer over Trading + Evaluation data. It never becomes a source of truth for anything (see Key Domain Decision KDD-04, Section 6).

### 4.6 Mistake Tracking Context
**Owns:** the mistake taxonomy (catalog of named error types) and the relationship between a trade and the mistakes tagged against it, plus the derived frequency/cost/priority ranking.
**Relationship to Trading Context:** a Trade references zero or more Mistakes; Mistake Tracking does not modify the Trade itself.

### 4.7 Journal Context
**Owns:** qualitative, free-text reflection — trade-level review notes and period-level (weekly) review entries.
**Relationship to Trading Context:** a Journal Entry may reference a specific Trade or a date range; it never contains scoring logic.

### 4.8 Identity & Access Context (Generic)
**Owns:** user identity, authentication, and — conditionally, only if Open Question 2 in the Product Bible resolves toward multi-user — authorization and account-level data isolation.

### 4.9 Preferences Context (Generic)
**Owns:** the "Settings" module exactly as scoped in Product Bible Section 9: theme, language, notification preferences, display preferences. Contains no business logic.

---

## 5. Context Map

```
                     ┌───────────────────────┐
                     │  Configuration Context │  (upstream — supplies rules)
                     └───────────┬───────────┘
                                 │ supplies criteria, weights, profiles, catalogs
                                 ▼
┌────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│ Trading Context│────▶│  Evaluation Context  │◀────│ (reads Checklist   │
│ (Trade is the  │ raw │  (CORE DOMAIN)       │     │  data captured at  │
│  source event) │data │                      │     │  trade time)       │
└───────┬────────┘     └──────────┬──────────┘     └───────────────────┘
        │                          │ produces EvaluationSnapshot
        │ referenced by            │ (attached back to the Trade)
        ▼                          ▼
┌────────────────┐     ┌─────────────────────┐
│ Playbook Context│◀───│  Analytics Context   │  (pure read-side; owns nothing)
│ (setup perf.)   │    │ (Statistics, Rolling)│
└────────────────┘     └─────────────────────┘
        ▲                          ▲
        │                          │
┌───────┴────────┐     ┌───────────┴─────────┐
│ Mistake Tracking│     │   Journal Context    │
│    Context      │     │ (qualitative review) │
└────────────────┘     └─────────────────────┘

┌────────────────────┐     ┌─────────────────────┐
│ Identity & Access   │     │ Preferences Context  │   (both Generic — no
│ Context (Generic)   │     │ (Generic)            │    upstream/downstream
└────────────────────┘     └─────────────────────┘    relationship to the above)
```

**Relationship types:**
- **Configuration → Evaluation**: Upstream/Downstream. Evaluation is a conformist consumer of whatever configuration currently exists — it does not get to negotiate the shape of that data.
- **Trading → Evaluation**: Upstream/Downstream, but the flow is bidirectional in effect: Trading supplies the raw facts, Evaluation supplies back an `EvaluationSnapshot` that attaches to the Trade permanently.
- **Trading/Evaluation → Analytics, Playbook**: Analytics and Playbook are pure downstream consumers — they never write back to Trading or Evaluation.
- **Trading → Mistake Tracking, Journal**: Downstream by reference — a Trade may reference Mistakes and Journal Entries, but those contexts never mutate a Trade.
- **Identity & Access, Preferences**: Deliberately unconnected to the trading domain graph — this is what makes them Generic (Section 3.3). Nothing in the Core or Supporting domains should ever need to know these contexts exist.

---

## 6. Key Domain Decisions

This section explains the reasoning behind the modeling choices most likely to be questioned or accidentally reversed by a future contributor who hasn't seen the reasoning. Each is written in decision-record form: context, decision, alternatives considered, reasoning, consequences.

### KDD-01: Five independent engines, not one composite score
**Context:** the archived `EVALUATION_ENGINE_SPECIFICATION.docx` proposed a single composite score built from five weighted dimensions.
**Decision:** five fully independent Engines, each producing its own Score.
**Alternatives considered:** the single-composite model above.
**Reasoning:** Process Over Outcome (Product Bible Principle 2) requires that, e.g., Quality never be diluted by Confidence or by outcome. Collapsing them into one number would make it impossible to say "this trade was executed perfectly but lost" — which is the exact insight the product exists to provide.
**Consequences:** more entities and more surface area than a single score, but each Score remains independently meaningful, independently auditable, and independently explainable (Domain Invariant DI-08, Section 14).

### KDD-02: EvaluationSnapshot and ChecklistSnapshot are not aggregate roots
**Context:** both could have been modeled as independently addressable aggregates with their own repositories and lookup paths.
**Decision:** both are owned by the `Trade` aggregate.
**Reasoning:** neither has a lifecycle independent of the Trade it belongs to, and treating them as child data of `Trade` matches how they actually behave in the Excel (a snapshot captured once, at trade time, never independently queried or modified).
**Consequences:** simpler transactional consistency (the whole `Trade` including its snapshots is one unit to save/load). If a future requirement needs a Checklist to exist before a specific Trade does (e.g., a general "market conditions today" check), `ChecklistSnapshot` must be promoted to its own aggregate — a foreseeable, not unforeseen, revision (Section 16).

### KDD-03: Configuration and Evaluation are separate bounded contexts
**Context:** business configuration (criteria, weights) could have been modeled as internal state of the Evaluation Context itself.
**Decision:** Configuration is a distinct upstream context.
**Reasoning:** the two have fundamentally different volatility and stakes — a configuration change is a deliberate, rare, high-consequence action (it can alter how every future trade is scored) while evaluation happens automatically on every trade. This is the same underlying logic as the Product Bible's own Configuration/Settings split (Section 9.1), applied one level deeper.
**Consequences:** Evaluation must always treat Configuration as an external, versioned dependency it reads, never a set of values it's free to assume are static or inline.

### KDD-04: Analytics owns no data of its own
**Context:** Analytics could persist its own computed/cached aggregates as independent facts.
**Decision:** Analytics is a pure read-side computation layer over Trading + Evaluation data, with no storage of its own beyond, at most, a performance cache that is never a source of truth.
**Reasoning:** this is the direct domain-level lesson from the Excel having ten near-identical statistics sheets before they were consolidated into one generic engine (`TRADEOS_MASTER_ROADMAP.md`, Section 7) — duplicated, independently-stored aggregates are exactly how a system drifts out of sync with its own source data.
**Consequences:** potential performance cost of computing statistics on demand at large trade volumes — an explicit, acceptable tradeoff deferred to the database design and Non-Functional Requirements discussion (Product Bible Sections 10.1–10.2), not solved by this document.

### KDD-05: Catalog entries are deactivated, never deleted
**Context:** hard deletion of unused Setups, Sessions, or Mistake Tags was considered.
**Decision:** soft deactivation only, while any Trade references the entry.
**Reasoning:** historical Trades must remain fully meaningful and attributable even after a Setup falls out of use — a direct requirement of Product Bible Principle 6 (Context Must Be Preserved).
**Consequences:** catalogs grow monotonically over time; hiding fully-deprecated entries from day-to-day UI views is a presentation-layer concern, not a deletion.

### KDD-06: Mistakes remain free-text today, despite the target model requiring identity-based references
**Context:** Domain Invariant DI-09 (Section 14) requires Trades to reference Catalog entries by stable identity, never copied text — but the Excel, and the code built so far, implement `Mistakes` as a free-text, comma-separated field.
**Decision:** this document describes the **target** model (Mistakes as a proper `CatalogEntry`) as canonical, and explicitly flags the current free-text implementation as acknowledged technical debt rather than silently treating it as consistent with the model.
**Reasoning:** consistent with the Product Bible's own posture of marking open questions rather than inventing answers (Product Bible Section 15, Open Question 6).
**Consequences:** this is the one place in this document where "the model" and "the current implementation" are known to diverge — any future document must not assume they already match.

### KDD-07 *(added v2.0)*: TradeStatus is independent of TradeResult; ROI %/P&L % are never stored
**Context:** `Trading_Journal_v2_0_Stable.xlsx`'s `📒 Trades` and `📒 Trades simple` sheets both carry an `Estado` column with three data-validated values — `No iniciado`, `Activo`, `Cerrado` — distinct from the `Resultado` column (`TP`/`BE`/`SL`). Confirmed by direct cell-level inspection (data validation lists, both sheets) as part of a Trade Entry redesign review. v1.1 of this document, formalized primarily from the Product Bible and a general reading of the Excel, collapsed both concepts into one `TradeResult` enum (`Open`/`TP`/`SL`/`BE`), never separately naming the "not yet executed" planning stage the Excel already supported. The same review also found `TP` (Take Profit) and `Margin` — present in both sheets, distinct from `Entry Price`/`Stop Loss` and from `Size` respectively — were never captured as owned Trade information in v1.1.
**Decision:** `TradeStatus` (`Planned`/`Open`/`Closed`) is introduced as a first-class concept, independent of `TradeResult`. `TakeProfit` and `MarginUsed` are added as owned Trade information (Section 8.1). Storing `ROI %` or `P&L %` as independent facts is explicitly rejected, even though the Excel's own `Trades simple` sheet stores `ROI` as a raw, trader-entered number (verified: not a formula) — both remain fully derivable (`ROI = realized_pnl / margin_used`; `P&L % = ROI / leverage`, the Excel's own literal formula) from facts already owned. `realized_pnl` itself is the one exception: the Excel enters it as a raw number too, but unlike `ROI` it is **not** derivable from any other fact this Trade owns (position size, leverage, and exchange fees/funding are never fully captured), so it remains an owned fact, never computed.
**Alternatives considered:** a fourth `TradeResult` value (`planned`) instead of a separate `TradeStatus` — rejected because it would keep mixing "what stage is this Trade at" with "what was its financial outcome," the exact conflation this decision exists to undo, and because the Excel itself keeps `Estado` and `Resultado` as two separate columns, not one.
**Reasoning:** direct evidence from the project's own declared source of truth (`PROJECT_AUDIT.md`'s and Section 1's own framing of the Excel as what this document is derived from) outranks a prior modeling simplification once the two are found to disagree — Section 20's own versioning process requires exactly this document to be revised first when an implementation-adjacent review reveals a concept was modeled incorrectly, never the reverse.
**Consequences:** every downstream document (Database Design, API Specification, Backend/Frontend Blueprints) that assumed `TradeResult` included `Open` must be revised in the same effort (see Section 20's own mandate for a MAJOR change) — tracked as this document's v2.0 revision, Section 21.

---

## 7. Aggregate Roots

An aggregate root is the only entry point through which its aggregate may be modified, and it is the unit that must remain internally consistent at every point in time.

| Aggregate Root | Bounded Context | Owns (inside its boundary) |
|---|---|---|
| **Trade** | Trading | Its own identity, price/size/direction facts, its `EvaluationSnapshot`, its `ChecklistSnapshot`, its list of tagged `MistakeReference`s, its MFE/MAE facts |
| **ScoringConfiguration** | Configuration | Its set of `ScoringCriterion` entities, its set of `ScoringWeight` entities (per `ScoringProfile`), its version history |
| **Catalog** | Configuration | A named reference list (Setups, Sessions, Strategies, Entry Triggers, Mistake Tags) and its active/inactive entries |
| **PlaybookSetup** | Playbook | Its own definition fields (entry/exit criteria, ideal conditions, risk rules); references trades by ID for performance attribution but does not own them |
| **JournalEntry** | Journal | Its own free-text content and the trade or date-range reference it is attached to |

**Explicit non-aggregates (by design — see KDD-02, Section 6):**
- `EvaluationSnapshot` is **not** its own aggregate root — it has no independent lifecycle or identity outside the `Trade` it belongs to.
- `ChecklistSnapshot` is treated as **owned by the Trade aggregate**, not a standalone aggregate.
- Analytics produces no aggregates at all — it is a pure computation/read layer over other contexts' data (Section 4.5, KDD-04).

---

## 8. Entities

For each entity: purpose, responsibilities, owned information, lifecycle, relationships, aggregate membership, invariants, business constraints, and future evolution.

### 8.1 Trade — *(Aggregate Root, Trading Context; Core Domain consumer)*

**Purpose:** the single record of one discretionary trading decision, from an optional planning stage, through entry, to (eventually) close.

**Responsibilities:** hold the ground-truth facts of what happened; enforce the invariants that make those facts internally consistent; expose the computed properties (R-multiple, MFE/MAE in R, Captured %, Potential Left, ROI %, P&L %) derived from its own facts, without ever storing them as independent facts.

**Owned Information:** market/instrument, direction, `status` (`Planned`/`Open`/`Closed`), entry price (present once `status != Planned`), stop loss, take profit, exit price (once Closed), size, margin used, leverage, `result` (`TP`/`SL`/`BE`, present only once Closed — `null` otherwise), realized P&L (a trader-supplied fact, sourced from the exchange, never derived — see Key Domain Decision below), timestamps (entered/closed — `entered_at` present once `status != Planned`), free-text notes, references to Strategy/Setup/Session/EntryTrigger (by identity, not by copy), its `EvaluationSnapshot` (present only once `status != Planned` — see Lifecycle), its `ChecklistSnapshot`, its tagged Mistakes, and the MFE/MAE raw prices (the favorable/adverse extremes reached).

**Lifecycle *(v2.0 — see Key Domain Decision KDD-07 below)*:** `Planned → Open → Closed (TP | SL | BE)`. `Planned` represents an idea or setup the trader intends to take but has not yet executed — no entry price, no entry timestamp, no Evaluation. `Open` requires an entry price and an entry timestamp; transitioning into it (whether directly at creation, or explicitly from `Planned`) is what triggers the Evaluation Engine for the first time (Domain Invariant DI-01, restated). A Trade may be amended while `Open` (price/size corrections) and amendments to a `Closed` trade should be tracked as a distinct event rather than silently overwriting history — see `TradeAmended` in Section 11.

**Relationships:** references (does not own) exactly one Strategy, one Setup, one Session, one Entry Trigger (each optional — a trade can exist with some classification fields unset, matching current Excel behavior); references zero or more Mistake Tags; owns exactly one `EvaluationSnapshot` and one `ChecklistSnapshot` once past `Planned`.

**Invariants:** see DI-01, DI-02, DI-06 (Section 14) and INV-TRADE-01/02/03/04 (Section 15).

**Future Evolution:** resolved, v2.0 — `Trade` is now modeled as always having the full set of optional fields; "Simple" is a UI presentation concern (which fields are shown), never a different shape of the entity itself. This is no longer a future evolution note; it is the current model.

See Key Domain Decision KDD-07 (Section 6) for the full context, decision, and reasoning behind `TradeStatus`, `TakeProfit`, `MarginUsed`, and the explicit rejection of storing `ROI %`/`P&L %`.

### 8.2 EvaluationSnapshot — *(Value Object owned by Trade, Evaluation Context)*

**Purpose:** the immutable record of what each of the five engines scored for this specific trade, at the moment it was scored.

**Responsibilities:** none beyond holding data — it has no behavior of its own. All scoring behavior lives in the `EvaluationEngine` domain service (Section 12).

**Owned Information:** for each of the five engines (Confidence, Quality, Execution, Market Context, Bias): the resulting score (0–100, or signed for Bias), the derived grade (where applicable), and the per-criterion breakdown (which criteria contributed, their raw values, their normalized values, their weights, their contributions) that produced it.

**Lifecycle:** created once, atomically with (or immediately after) the Trade it belongs to. **Never modified in place.** If a trade is re-evaluated, this produces a *new* `EvaluationSnapshot`, and the old one is retained as history, not overwritten (DI-05, Section 14).

**Relationships:** belongs to exactly one Trade; conceptually produced by reading one `ChecklistSnapshot` plus the Trade's own facts, through the current (or a specified historical version of the) `ScoringConfiguration`.

**Business Constraints:** an `EvaluationSnapshot` must never be constructible without a full breakdown (DI-08, Section 14).

**Future Evolution:** a sixth engine (or more) should be addable without changing this entity's shape beyond adding another named slot (Section 16).

### 8.3 ChecklistSnapshot — *(Entity owned by Trade, Evaluation Context)*

**Purpose:** the pre-trade context capture that supplies the raw inputs the Evaluation Engine's Confidence, Market Context, and Bias engines read from.

**Responsibilities:** hold the trader's pre-trade answers (HTF alignment, emotional state, LTF confirmation, macro readings, market structure readings, etc.) as a permanent record of "what the world looked like when this decision was made" — independent of what the Evaluation Engine later computes from it.

**Owned Information:** the raw categorical and numeric answers to every checklist question defined in Configuration's criteria catalog (Section 8.4) at the time the trade was taken.

**Lifecycle:** created once, at or before trade entry; read-only afterward.

**Relationships:** belongs to exactly one Trade; its fields are read by the Evaluation Engine (Section 12) as input, but it is not owned by the Evaluation Context.

**Future Evolution:** see KDD-02 (Section 6) for the reasoning and the foreseeable revision this decision may require.

### 8.4 ScoringCriterion — *(Entity within ScoringConfiguration aggregate, Configuration Context)*

**Purpose:** the definition of one measurable input to one Evaluation engine.

**Owned Information:** a stable identifier (never a row position), the engine it belongs to, an optional category grouping, a human-readable name and description, the source field it reads, its expected numeric range, and — for categorical criteria — a lookup table mapping category labels to normalized sub-scores.

**Lifecycle:** created when a new criterion is defined; can be deactivated (excluded from scoring) without being deleted, so historical `EvaluationSnapshot`s that referenced it while active remain fully meaningful.

**Relationships:** belongs to the `ScoringConfiguration` aggregate; referenced by one or more `ScoringWeight` entities (one per profile it participates in).

**Invariants:** see INV-CRITERION-01/02 (Section 15).

**Future Evolution:** new criteria must be addable without touching the aggregation logic of the engine that uses them.

### 8.5 ScoringWeight — *(Entity within ScoringConfiguration aggregate, Configuration Context)*

**Purpose:** how much one criterion counts, for one scoring profile.

**Owned Information:** a reference to the `ScoringCriterion` it weights (by stable ID), the `ScoringProfile` it applies to, its numeric weight, whether it is currently active, and a version marker.

**Lifecycle:** weights can change over time; every change should be capable of being versioned so that "what weights were in effect when trade X was scored" remains an answerable question indefinitely.

**Invariants:** see INV-WEIGHT-01 (Section 15).

### 8.6 ScoringConfiguration — *(Aggregate Root, Configuration Context)*

**Purpose:** the single, versionable source of truth for how all five Evaluation engines currently compute their scores.

**Responsibilities:** hold the full set of `ScoringCriterion` and `ScoringWeight` entities; guarantee that a given version of this configuration is a complete, internally consistent snapshot that can be pointed to by ID from any `EvaluationSnapshot` that used it.

**Lifecycle:** versioned, not overwritten (DI-06, Section 14).

**Future Evolution:** this is also where a sixth `ScoringProfile` would be added — as new rows referencing existing criteria, never as a change to the aggregation logic itself.

### 8.7 Catalog & CatalogEntry — *(Aggregate Root / Entity, Configuration Context)*

**Purpose:** the named reference lists shared across the system — Setups, Sessions, Strategies, Entry Triggers, and Mistake Tags.

**Owned Information:** a catalog has a kind (which list it is) and a set of entries, each with a name and an active/inactive flag.

**Lifecycle:** entries can be deactivated without deletion (KDD-05, Section 6).

**Relationships:** referenced by `Trade` (Setup, Session, Strategy, Entry Trigger) and by `Trade`'s tagged mistakes (Mistake Tags catalog).

**Business Constraint:** see DI-09 (Section 14). **Exception, explicitly flagged as unresolved (KDD-06, Section 6; Product Bible Open Question 6):** Mistake Tags currently remain free-text in the Excel and in the code built so far.

### 8.8 PlaybookSetup — *(Aggregate Root, Playbook Context)*

**Purpose:** the living definition of one trading setup — what it is, when it applies, and how it has actually performed.

**Owned Information:** name/description, entry criteria, exit criteria, ideal market conditions, risk management rules, example references (e.g., screenshots), and a reference to its corresponding `Catalog` entry so that Trading Context trades attributed to this setup can be found.

**Lifecycle:** a living document — expected to be edited over time. Performance data is never stored on the `PlaybookSetup` itself — it is always a live read from the Analytics Context, attributed by the setup's catalog reference.

**Future Evolution:** version history for setup definitions is a natural extension — a `PlaybookSetup` could gain the same versioning treatment as `ScoringConfiguration` (Section 8.6) if the trader wants to track how a setup's own definition changed over time, separate from its performance.

### 8.9 MistakeTag — *(CatalogEntry specialization, Mistake Tracking Context)*

**Purpose:** one named category of trading error (e.g., "FOMO," "Moved Stop Loss").

**Relationships:** referenced by zero or more Trades. Frequency, cost, and priority ranking are computed by the Mistake Tracking Context by querying Trades that reference a given tag — Mistake Tracking owns no trade data itself.

### 8.10 JournalEntry — *(Aggregate Root, Journal Context)*

**Purpose:** free-text qualitative reflection, either attached to a specific Trade or to a period (e.g., a week).

**Owned Information:** the free-text content, its creation/edit timestamps, and either a Trade reference or a date-range reference (never both).

### 8.11 UserAccount — *(Aggregate Root, Identity & Access Context — Generic)*

**Purpose:** the identity of the person using TradeOS.

**Note on current scope:** as of this document, exactly one `UserAccount` is assumed to exist in practice (Product Bible Section 4.2). This entity is modeled now, minimally, so that every other aggregate in this document can reference "the current user" without redesign later — but no multi-tenancy, permissions, or sharing behavior should be built against it until Product Bible Open Question 2 (business model) resolves.

### 8.12 UserPreferences — *(Aggregate Root, Preferences Context — Generic)*

**Purpose:** theme, language, notification settings, display preferences — exactly the Product Bible Section 9's "Settings" module, and nothing more.

---

## 9. Value Objects

Value objects have no identity of their own — two value objects with the same data are interchangeable, and they are never independently looked up by ID.

- **Money/PnL** — an amount with an implied currency; always attached to a Trade, never a standalone concept.
- **Price** — a positive numeric value in the instrument's quote terms (Entry Price, Stop Loss, Exit Price, MFE Price, MAE Price all use this shape).
- **RMultiple** — the risk-normalized outcome of a trade — always computed, never stored as an independent fact.
- **Score** — a 0–100 (or signed, for Bias) numeric value plus its derived `Grade`. A `Score` without its breakdown is considered incomplete.
- **Grade** — A+ / A / B / C / D, always derived from a `Score`, never assigned independently.
- **DateRange** — a start and end used by period-scoped Analytics queries and period-scoped `JournalEntry`s.
- **CriterionBreakdownRow** — one line of a `Score`'s explanation: criterion name, raw value, normalized value, weight, contribution. Exists only inside an `EvaluationSnapshot`.

---

## 10. Enums

- **Direction**: `Long`, `Short`.
- **TradeResult**: `Open`, `TP`, `SL`, `BE`.
- **EngineType**: `Confidence`, `Quality`, `Execution`, `MarketContext`, `Bias`.
- **NormalizationStrategy**: `Unsigned` (strength/clarity), `Signed` (direction).
- **ScoringProfile**: `DayTrading`, `SwingTrading`, `Scalping`.
- **GradeLabel**: `A+`, `A`, `B`, `C`, `D`.

---

## 11. Business Events

Domain events represent something that has happened, is immutable historical fact, and may be of interest to other parts of the system (or, later, other bounded contexts entirely — e.g., an AI Coach reacting to events rather than polling state).

| Event | Raised By | Meaning | Who Might Care |
|---|---|---|---|
| **TradeRegistered** | Trading Context | A new Trade was captured | Evaluation (must produce a snapshot), Analytics (must include it in future aggregations) |
| **TradeEvaluated** | Evaluation Context | An `EvaluationSnapshot` was produced for a Trade | Analytics, Playbook (for setup attribution) |
| **TradeClosed** | Trading Context | A Trade transitioned from Open to a terminal Result | Analytics, Mistake Tracking (final mistake tagging often happens at close) |
| **TradeAmended** | Trading Context | A Trade's facts were corrected after initial capture | Anything that already read the prior facts and cached them |
| **MistakeTagged** | Mistake Tracking Context | A Mistake was attached to a Trade | Mistake Tracking's own frequency/cost aggregation |
| **ScoringConfigurationChanged** | Configuration Context | A new version of criteria or weights was published | Evaluation (future trades use the new version); optionally triggers a "recalculate historical trades" action, which is itself a distinct, explicit operation, never implicit |
| **PlaybookSetupUpdated** | Playbook Context | A setup's definition changed | Nothing automatic — this is a documentation change, not a scoring change |
| **CatalogEntryDeactivated** | Configuration Context | A Setup/Session/Strategy/Entry Trigger/Mistake Tag was deactivated | UI (should stop offering it for new trades) — must never affect existing Trade references |

---

## 12. Domain Services

Domain services hold behavior that doesn't naturally belong to a single entity because it operates across or above them.

### 12.1 EvaluationEngine
The Core Domain's central service. Given a `ChecklistSnapshot` and/or `Trade` facts, the currently-active (or a specified historical version of) `ScoringConfiguration`, and a `ScoringProfile` where relevant, produces an `EvaluationSnapshot`. This is a pure function of its inputs — it holds no state of its own and must be trivially testable in isolation, exactly as it already is in the code built so far (`app/domain/evaluation_engine.py`), which is the reference implementation this document formalizes.

### 12.2 StatisticsAggregationService
Belongs to the Analytics Context. Computes Win Rate, Expectancy, Profit Factor, Average R, and related metrics over any set of Trades. Written once, generically, and reused for every grouping (KDD-04, Section 6).

### 12.3 MistakePriorityRankingService
Belongs to the Mistake Tracking Context. Given the set of Trades referencing each `MistakeTag`, computes frequency, total cost, and a combined priority ranking ("fix this first").

### 12.4 PlaybookRecommendationService
Belongs to the Playbook Context. Given `StatisticsAggregationService` output grouped by setup, identifies which setups are candidates for promotion or de-emphasis in the Playbook — always a suggestion surfaced for the trader to act on, never an automatic edit to a `PlaybookSetup`.

---

## 13. Entity Lifecycles

### 13.1 Trade *(v2.0 — three stages, see KDD-07)*
```
[ not yet created ]
        │  register (status chosen explicitly: Planned or Open)
        ▼
   ( Planned ) ──amend──▶ ( Planned )      [no Evaluation yet]
        │
        │  open (Entry Price + Entry Date supplied together;
        │        first Evaluation runs here)
        ▼
     ( Open ) ──amend──▶ ( Open )
        │
        │  close (Result + Exit Price + Realized P&L supplied together)
        ▼
     ( Closed: TP | SL | BE ) ──amend──▶ ( Closed ) [raises TradeAmended, not silently]
```
A Trade registered directly as `Open` (or already-`Closed`, per API Spec §6.4's "may be supplied now") skips the `Planned` stage entirely — `Planned` is optional, never mandatory, exactly mirroring the Excel's own usage (most rows go straight to `Activo`/`Cerrado`; `No iniciado` is used only when the trader genuinely has not acted yet).

### 13.2 ScoringConfiguration
```
[ v1 published ] ──change (new criterion / weight / profile)──▶ [ v2 published ]
       │                                                              │
       │ referenced forever by EvaluationSnapshots created under v1  │ (same, for v2)
       ▼                                                              ▼
   (immutable historical record — never edited after superseded)
```

### 13.3 CatalogEntry (Setup, Session, Strategy, Entry Trigger, Mistake Tag)
```
( Active ) ──deactivate──▶ ( Inactive, still referenceable by historical Trades )
    ▲                                │
    └──────────── reactivate ────────┘
```

### 13.4 PlaybookSetup
```
( Active, being traded ) ──edit definition──▶ ( Active, revised definition )
         │
         │ trader decides to stop using it
         ▼
   ( Deprecated — retained for historical attribution, not offered for new Trades )
```

---

## 14. Domain Invariants

These are the fundamental truths of the TradeOS business domain. They must hold regardless of implementation — regardless of database, programming language, or API design. They are stated here at the conceptual level; Section 15 (Business Constraints Registry) is where each is given a specific, enforceable ID and an implementation-facing enforcement point.

- **DI-01:** A Trade's realized facts, once Closed, do not silently change. Any correction is an explicit, tracked event (`TradeAmended`), never an invisible overwrite.
- **DI-02:** In a Long Trade, Stop Loss is always below Entry Price; in a Short, always above.
- **DI-03:** Quality is always computed independent of a Trade's financial outcome. No implementation may make Quality a function of P&L, directly or indirectly.
- **DI-04:** Market Context is always computed independent of Bias's direction — a Market Context Score never encodes which way the market is expected to move, only how clearly it is signaling.
- **DI-05:** Exactly one Engine (Bias) uses signed normalization; all four others use unsigned. Introducing a second signed engine is a deliberate, reviewed design decision (see Key Domain Decisions, Section 6), never an incidental implementation detail.
- **DI-06:** An `EvaluationSnapshot`, once created, is never mutated — only superseded by a new snapshot from a subsequent, explicit re-evaluation. The same holds for `ScoringConfiguration` versions.
- **DI-07:** A change to `ScoringConfiguration` never retroactively alters the meaning of a past `EvaluationSnapshot` — history is never rewritten by a later change in rules.
- **DI-08:** Every Score must be explainable — a Score without a retrievable breakdown of the criteria that produced it is an invalid state, not merely an incomplete one.
- **DI-09:** A Trade references Catalog entries by stable identity, never by copied text (with the single, explicitly flagged exception of `Mistakes` today — KDD-06, Section 6).
- **DI-10:** Catalog entries are never deleted while any Trade references them — deactivation, not deletion, is the only removal mechanism.
- **DI-11:** Analytics never becomes a source of truth — any statistic must be reproducible on demand from Trading + Evaluation data alone, never from Analytics' own independently-drifting copy.
- **DI-12:** Captured % is defined only for TP trades; it is never expressed as a negative number for a losing trade.
- **DI-13 *(added v2.0)*:** A `Planned` Trade is never scored by the Evaluation Engine and never contributes to any Analytics figure — Evaluation and Analytics both operate exclusively on Trades that have reached at least `Open`.
- **DI-14 *(added v2.0)*:** ROI % and P&L % are always computed from `realized_pnl`/`margin_used`/`leverage` at read time — never stored as independent facts (KDD-07, Section 6).

---

## 15. Business Constraints Registry

This consolidates the enforceable, implementation-facing form of the Domain Invariants above (Section 14), plus the audit's discovered rules, into one registry so future documents can cite a single ID rather than re-deriving the rule.

| ID | Rule | Realizes | Enforced By |
|---|---|---|---|
| INV-TRADE-01 | Long: Stop < Entry. Short: Stop > Entry — only checked once both exist (never for `Planned`) | DI-02 | Trade aggregate, at creation/amendment/open |
| INV-TRADE-02 *(redefined v2.0)* | `status=Planned` ⟺ no Entry Price/Entry Date/Result/Exit Price/Realized P&L. `status=Open` ⟺ Entry Price + Entry Date present, Result/Exit Price/Realized P&L absent. `status=Closed` ⟺ Result + Exit Price + Realized P&L present together | DI-01 | Trade aggregate |
| INV-TRADE-03 (= audit BR-009) | Capital-before is derived sequentially from the prior Trade's capital-after + injections | — | Trading Context (explicit, not implicit) |
| INV-TRADE-04 *(added v2.0)* | A `Planned` Trade may transition only to `Open`, never directly to `Closed` | DI-13 | Trade aggregate |
| INV-CRITERION-01 | Criteria are identified by stable ID, never row position | — | ScoringConfiguration aggregate |
| INV-CRITERION-02 | A criterion belongs to exactly one engine | — | ScoringConfiguration aggregate |
| INV-WEIGHT-01 | Aggregation divides by the sum of *active* weights only | — | EvaluationEngine domain service |
| INV-QUALITY-01 (= audit BR-003) | Trade Quality is computed independent of P&L | DI-03 | EvaluationEngine domain service |
| INV-CONTEXT-01 (= audit BR-004) | Market Context Score is computed independent of Bias direction | DI-04 | EvaluationEngine domain service |
| INV-CAPTURE-01 (= audit BR-007) | Captured % is only defined for TP trades | DI-12 | Trade aggregate (computed property) |
| INV-POTENTIAL-01 (= audit BR-008) | Potential Left uses `MAX(0, R-multiple)` as its baseline | — | Trade aggregate (computed property) |
| INV-CATALOG-01 | A Trade references catalog entries by identity, never by copied text | DI-09 | Trading + Configuration Context boundary |

---

## 16. Future Extensibility

This document is written so that the following, all named in Product Bible Section 12 (Future Vision), require **no change to the strategic design (Sections 3–5)** — only additive tactical modeling:

- **A sixth Evaluation engine** — a new `EngineType` enum value, a new set of `ScoringCriterion`/`ScoringWeight` rows, and a new named slot in `EvaluationSnapshot`. The Core Domain's shape does not change.
- **Pattern Discovery (Intelligence Layer)** — a new domain service alongside `StatisticsAggregationService` in the Analytics Context, reading the same Trade/Evaluation data, producing recommendations rather than aggregates. No new bounded context required.
- **AI Coaching Layer** — modeled as a new, downstream bounded context that *consumes* Business Events (Section 11) and Analytics output, and produces conversational responses. It should never become a source of truth for any entity defined here.
- **Multi-account / multi-user** — conditional on Product Bible Open Question 2. If it resolves toward yes, `UserAccount` (Section 8.11) gains a real authorization model, and every aggregate root in this document gains an implicit "owned by which account" scoping — a mechanical, additive change to every aggregate, not a redesign of any of them, provided this document's aggregate boundaries were respected during implementation.

---

## 17. Future Reserved Domains

These are domains intentionally **not modeled yet**, reserved so that when they are built, their names and boundaries are already agreed rather than improvised under time pressure. Naming them now prevents a future contributor from accidentally redefining an existing context's boundary to absorb one of these instead of giving it its own.

- **Intelligence / Pattern Discovery Domain** — reserved for Product Bible Future Vision 12.2. Will consume Trading/Evaluation/Analytics data to surface multi-variable performance patterns; must never become a new source of truth (consistent with DI-11).
- **AI Coaching Domain** — reserved for Product Bible Future Vision 12.3. Strictly downstream: consumes Business Events (Section 11) and Analytics output; never authors facts about a Trade or an Evaluation.
- **Notification / Alerting Domain** — implied by the "reminders" concept in `TradeOS_PRODUCT.docx` v1.0 and by `UserPreferences`' notification settings (Section 8.12). Not modeled yet because no entity in this document currently needs to trigger a notification — reserved so that when one does (e.g., a Checklist incompletion), the domain that delivers it is a distinct concern from the domain that detects it.
- **Broker / Exchange Integration Domain** — reserved for Product Bible Future Vision 12.4 (Ecosystem & Automation). Would sit *upstream* of the Trading Context (automatically supplying the data that triggers `TradeRegistered`), not replace Trading Context itself.
- **Multi-Account / Tenancy Domain** — reserved, conditional on Product Bible Open Question 2. Would extend Identity & Access Context (Section 4.8), not replace it.
- **Reporting / Export Domain** — implied by the "Exportable Reports" feature in `TradeOS_PRODUCT.docx` v1.0. Reserved as a thin, stateless downstream consumer of Analytics — never a new data owner, consistent with DI-11.

---

## 18. Traceability Appendix

| Domain Concept | Product Bible Reference | Excel Reference |
|---|---|---|
| Trade | Section 9, "Trades" module | `📒 Trades` (66 columns, institutional detail) and `📒 Trades simple` (17 columns) — `TradeStatus` (v2.0) traces to both sheets' `Estado` column; `TakeProfit`/`MarginUsed` (v2.0) trace to both sheets' `TP`/`Margin` columns |
| ChecklistSnapshot | Section 9, "Checklist" module | `CHECKLIST` |
| EvaluationSnapshot / EvaluationEngine | Section 8 (entire) | Score columns in `📒 Trades`; weights in `⚙️ CONFIG` |
| ScoringConfiguration / ScoringCriterion / ScoringWeight | Section 9, "Configuration" module | `⚙️ CONFIG` — `MARKET_CONTEXT_CRITERIA`, `MARKET_CONTEXT_WEIGHTS`, and the linear engines' weight cells |
| Catalog / CatalogEntry | Section 9, "Configuration" module | `⚙️ CONFIG` — `SETUP_LIST`, `SESSION_LIST`, `STRATEGY_LIST`, `ENTRY_TRIGGER_LIST`, `MISTAKE_TAGS` |
| PlaybookSetup | Section 9, "Playbook" module | `📘 PLAYBOOK` |
| MistakeTag | Section 9, "Mistakes" module | `🚫 Errores` |
| JournalEntry | Section 9, "Journal / Review" module | `📝 Revisión de Trades`, `WEEKLY REVIEW` |
| StatisticsAggregationService | Section 9, "Statistics" / "Rolling Statistics" modules | `📊 Estadísticas`, `Stats por Estrategia/Set Up/Entry Trigger`, `⏱️ Stats por Tiempo`, `📈 EXPECTANCY`, `📈 Rolling Statistics` |
| UserAccount | Section 4.2 | *(no Excel equivalent — single-file, single-user by construction)* |
| UserPreferences | Section 9, "Settings" module | *(no Excel equivalent — see Product Bible Section 9.2)* |

Any future database table, API endpoint, backend service, frontend feature, or AI module must appear as a row (or an addition to a row) in a table shaped like this one before it is built — that is what "traceable back to this document" means in practice.

---

## 19. Explicit Non-Goals of This Document

- No table names, column types, indexes, or storage engine choices — reserved for the database design document, to be written next only after this document is approved.
- No API endpoint paths or HTTP verbs.
- No UI layout or component decisions.
- No resolution of any Open Foundational Question from `TRADEOS_PRODUCT_BIBLE.md` Section 15 — where this document had to make a modeling choice that touches one of those questions (e.g., `UserAccount`, Section 8.11), it explicitly flags the choice as provisional and conditional, not as an answer to the open question.

---

## 20. Domain Model Versioning

This document will change over time. How it may change, and how those changes are managed, is itself part of the canonical model.

- **This document is versioned independently of the code and database design that implement it.** A downstream document (database schema, API specification) must declare which version of this Domain Model it was written against, so that a future Domain Model change can identify exactly which downstream documents require re-review.
- **A MAJOR version change** redefines an existing concept's meaning — e.g., changing what "Quality" measures, merging two Bounded Contexts, or promoting `ChecklistSnapshot` to its own aggregate root. This requires the same review and approval rigor as the original freeze of this document, because downstream documents may already assume the prior meaning.
- **A MINOR version change** adds a new concept without altering any existing one — e.g., a new `EngineType` enum value, activating one of the Future Reserved Domains (Section 17), or adding a new `ScoringProfile`. This does not require re-approving the whole document, but does require updating the Traceability Appendix (Section 18) in the same revision.
- **A PATCH version change** is a clarification, typo fix, or added cross-reference with no semantic change, and does not require formal review.
- **Every MAJOR or MINOR change must update, in the same revision:** the Traceability Appendix (Section 18), and — if the change touches an invariant — both the Domain Invariants (Section 14) and Business Constraints Registry (Section 15). These sections must never be allowed to drift out of sync with the entities they describe.
- **No implementation detail may retroactively redefine a Domain Model concept.** If building the database design or the backend reveals that a concept in this document was modeled incorrectly, this document is revised *first*, as its own reviewed change, and downstream artifacts follow — never the reverse. An implementation detail is never allowed to silently become the de facto model.

---

## 21. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial canonical Domain Model. Derived from `TRADEOS_PRODUCT_BIBLE.md` v2.1 and the Excel-confirmed business logic in `PROJECT_AUDIT.md`. Covered strategic design, tactical design, and future extensibility. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Added Ubiquitous Language / Glossary (Section 2), Key Domain Decisions (Section 6), Domain Invariants (Section 14, distinct from and complementary to the existing Business Constraints Registry), Future Reserved Domains (Section 17), and Domain Model Versioning (Section 20). Renumbered all sections accordingly. |
| 2.0 | 2026-07-30 | **MAJOR** (Section 20 process followed): redefined the Trade lifecycle. Introduced `TradeStatus` (`Planned`/`Open`/`Closed`) as a concept independent of `TradeResult` (now `TP`/`SL`/`BE`/`null` — `Open` removed as a result value). Added `TakeProfit`/`MarginUsed` as owned Trade information. Added Key Domain Decision KDD-07 (Section 6) documenting the trigger (direct inspection of `Trading_Journal_v2_0_Stable.xlsx`'s `Estado`/`TP`/`Margin` columns, present in both `📒 Trades` and `📒 Trades simple`, never captured in v1.1) and the explicit rejection of storing `ROI %`/`P&L %` as independent facts (always computed from `realized_pnl`/`margin_used`/`leverage`). Added DI-13/DI-14 (Section 14), redefined INV-TRADE-02 and added INV-TRADE-04 (Section 15), updated the Trade lifecycle diagram (Section 13.1) and the Traceability Appendix (Section 18) in the same revision, per this section's own mandate. |

**Status:** FROZEN. This is the second permanent foundational document of TradeOS, after `TRADEOS_PRODUCT_BIBLE.md`.
**Next document per the reconstruction plan:** database design (schemas, tables), to be created only now that this Domain Model is approved.
