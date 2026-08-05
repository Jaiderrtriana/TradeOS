# TRADEOS_DATABASE_DESIGN.md

**Document Status:** CANONICAL AND FROZEN — the permanent database design of TradeOS.
**Version:** 1.2
**Last Updated:** 2026-07-30
**Depends On:** `TRADEOS_PRODUCT_BIBLE.md` v2.1, `TRADEOS_DOMAIN_MODEL.md` v2.0, `TRADEOS_SYSTEM_ARCHITECTURE.md` v1.1 (all frozen). This document does not redefine any business rule, entity, or architectural decision made in those three — it defines how they are physically stored.
**Relationship to the Excel:** `Trading_Journal_v2_0_Stable.xlsx` remains authoritative for *validated business rules* (per `PROJECT_AUDIT.md`), but this schema is designed from the Domain Model outward, not from the Excel's sheets inward. Any resemblance between a table here and an Excel sheet is coincidental, not causal.
**Is Not:** SQL, a Prisma/ORM schema, or a migration script. This document describes the schema precisely enough for another engineer to write those artifacts without making a single architectural decision of their own.

---

## 1. Design Goals

This schema exists to make permanent, in storage, the guarantees the first three foundational documents already promised in principle. Concretely:

1. **The database must never be the reason a historical fact silently changes.** Domain Invariants DI-01, DI-06, and DI-07 (`TRADEOS_DOMAIN_MODEL.md` Section 14) are not application-layer suggestions — they are schema-level guarantees, enforced by what is (and is not) updatable in place versus versioned versus append-only.
2. **The database must never force a design choice the business didn't ask for.** Every table below traces to a Domain Model entity, aggregate, or value object (Section 15, Traceability Matrix). Nothing is added because "a SaaS usually has this table" — that would violate `TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 4 (Simplicity Until Proven Insufficient) at the storage layer.
3. **Extending the Evaluation Engine (a sixth engine, a new criterion, a new profile) must be a data change, never a schema change.** This is the single hardest requirement in this document and it shapes Section 7 more than anything else.
4. **Every score must remain reproducible indefinitely.** A historical `EvaluationSnapshot` must be explainable — which criteria, which weights, which configuration version — years after the configuration that produced it has been superseded.
5. **The schema must not know, or care, whether TradeOS ever becomes multi-user.** Where a decision is genuinely conditional on Product Bible Open Question 2, this document says so and designs the *cheapest-to-extend* option today rather than guessing the full future shape.
6. **Correctness and historical integrity outrank performance**, exactly as `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9 (Quality Attributes Matrix) already ranked them. Where a normalization choice costs a join that a denormalized column would avoid, normalization wins unless explicitly justified otherwise (Section 10).

---

## 2. Database Architecture

### 2.1 Engine
**PostgreSQL**, per `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8 (ADR-06) — chosen there specifically for strong relational integrity alongside JSONB flexibility, both of which this schema relies on heavily (Section 7).

### 2.2 Schema Organization

One PostgreSQL **schema** (namespace) per Bounded Context module, exactly matching `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3's module list. This is a deliberate choice: it makes the Architecture document's "modules communicate only through published contracts, never by reaching into another module's tables" (Architectural Principle 2) enforceable at the database permission level, not just a code-review convention.

| Postgres Schema | Bounded Context | Tables? |
|---|---|---|
| `identity` | Identity & Access (Generic) | Yes |
| `preferences` | Preferences (Generic) | Yes |
| `configuration` | Configuration | Yes |
| `trading` | Trading | Yes |
| `playbook` | Playbook | Yes |
| `journal` | Journal | Yes |
| `evaluation` | Evaluation (Core Domain) | **No tables — see Section 3.1** |
| `analytics` | Analytics | **No tables — see Section 3.1** |
| `mistake_tracking` | Mistake Tracking | **No tables — see Section 3.1** |
| `platform` | Cross-cutting (not a Bounded Context) | Yes — one table (Section 2.6) |
| `ai`, `notifications`, `integrations`, `reporting` | Future Reserved Domains | **Reserved, empty — see Section 12** |

### 2.3 Naming Conventions

- Tables: `snake_case`, plural (`trades`, `catalog_entries`).
- Columns: `snake_case`, singular (`entry_price`, not `entry_prices`).
- Primary key column: always `id`.
- Foreign key columns: `<referenced_concept>_id` (e.g., `strategy_id` referencing a `catalog_entries` row, not `catalog_entry_id` — the column name reflects the *business* reference, not the physical table, since one table (`catalog_entries`) backs several distinct business references — see Section 4).
- Enum-like lookup tables: plural noun naming the set (`engine_types`, `scoring_profiles`).
- Junction (many-to-many) tables: `<owning_entity>_<referenced_entity>` (e.g., `trade_mistakes`).

### 2.4 UUID Strategy

**All primary keys are UUIDv4**, generated by the application (not the database), with one deliberate, documented exception (Section 2.4.1).

**Why UUID over auto-incrementing integers:**
- Matches the existing reference implementation (`tradeos-backend`'s `GUID` type), avoiding a migration of already-written code.
- Supports `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.3's module extraction path: if a module is ever pulled into its own deployed service, its records' identities do not collide with another module's, which a shared auto-increment sequence could risk.
- Does not leak information (a sequential integer ID reveals how many rows exist and roughly when a row was created; a UUID does not) — a small, free Security (Section 11) benefit.

**Why application-generated, not database-generated (`gen_random_uuid()` as a column default):** the application (specifically, each module's domain layer) already constructs its aggregate roots with an identity before persistence (Domain Model — every aggregate root is a Python dataclass with `id: UUID = field(default_factory=uuid4)` today). Letting the database also be capable of generating one would create two sources of truth for "how is an ID assigned." The database column still declares a default of `gen_random_uuid()` as a safety net for any direct-insert path (e.g., a data migration script), but the application is expected to always supply its own.

#### 2.4.1 Exception: `scoring_criteria.id`

`scoring_criteria` uses a **stable, human-assigned string identifier** (e.g., `"HTF_ALIGN"`, `"bias_index"`) as its primary key, not a UUID. This is a deliberate deviation, justified because:
- Domain Invariant INV-CRITERION-01 (`TRADEOS_DOMAIN_MODEL.md` Section 15) requires criteria to be "identified by a stable ID, never row position" — the *point* of this ID is to be a human-legible, stable slug referenced directly in configuration exports, code, and documentation, not an opaque surrogate.
- The existing reference implementation already models criteria this way (`ScoringCriterion(id="bias", ...)`).
- This is the **only** table in the entire schema with a non-UUID primary key. Any future table proposing a similar natural key must document equally strong justification, per Architectural Principle 8 (Every Decision Is Traceable).

### 2.5 Timestamp Strategy

- Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Most mutable tables additionally have `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`, maintained by the application (not a database trigger, to keep the "who changed this and why" logic visible in application code rather than hidden in the database — consistent with Architectural Principle 3, Explicit Over Implicit).
- All timestamps are stored in UTC (`TIMESTAMPTZ`, never `TIMESTAMP WITHOUT TIME ZONE`). Local-time display is a `preferences` concern (Section 3), never a storage concern.
- **Business timestamps are distinct from audit timestamps.** `trades.entered_at` and `trades.closed_at` are business facts (when the trade actually happened) and are never confused with `trades.created_at`/`updated_at` (when the database row was written/modified) — a trade entered retroactively could have an `entered_at` in the past and a `created_at` of right now, and both must remain independently meaningful.

### 2.6 Soft Delete Strategy

TradeOS uses **two distinct mechanisms**, never conflated, because they answer two different business questions:

1. **Deactivation** (`is_active BOOLEAN`) — for `configuration.catalog_entries` and `configuration.scoring_criteria`/`scoring_weights`. Answers: "is this still offered for new use?" A deactivated row is not deleted, is not hidden from historical queries, and continues to satisfy every foreign key that already points to it. This directly implements Domain Invariant DI-10.
2. **Soft delete** (`deleted_at TIMESTAMPTZ NULL`) — for genuinely mutable aggregates where a record might represent a real data-entry mistake: `trading.trades`, `journal.journal_entries`, `playbook.playbook_setups`. A non-null `deleted_at` means "the trader marked this record as never having been valid" (e.g., a duplicate trade entered twice) — distinct from a `Closed` trade, which is fully valid history, not deleted. **Nothing is ever hard-deleted** (no `DELETE FROM` in the application's normal operation) — this is what "historical data must never be silently modified" (this document's mandate) means concretely.

`evaluation_snapshots`, `checklist_snapshots`, and `evaluation_snapshot_breakdowns` have **no delete mechanism of any kind, soft or hard** — they are append-only, immutable once written, per Domain Invariant DI-06. If a Trade is soft-deleted, its snapshots remain in storage, orphaned but intact, in case the soft delete is ever reversed or audited.

### 2.7 Audit Strategy

- Every table capable of being created by a user action carries a nullable `created_by_user_id UUID` (references `identity.user_accounts`), populated now (even with a single confirmed user, Product Bible Section 4.2) specifically so that retrofitting ownership later — if Product Bible Open Question 2 resolves toward multi-user — is a data backfill, not a schema migration. This is the one place this document adds a column ahead of a confirmed need, and it is justified explicitly: the cost today is one nullable column; the cost of adding it later, after real historical data exists with no owner recorded, is materially higher.
- A single cross-cutting **`platform.event_log`** table (Section 6.16) durably records every Domain Event named in `TRADEOS_DOMAIN_MODEL.md` Section 11 as it fires, satisfying Architectural Principle 5 (Observability Is Not Optional) at the storage layer: even if no module currently subscribes to an event, its occurrence is never lost.
- This is deliberately **not** a field-level audit trail (i.e., not a table recording every historical value of every column on every change) — that would be a Security/Observability investment disproportionate to the Quality Attributes Matrix's current ranking (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9 ranks Security 5th, below Correctness/Reliability/Maintainability/Extensibility) and to Architectural Principle 4. If deeper field-level audit is ever required (e.g., by a future compliance need under Open Question 3), it is an additive table, not a redesign.

---

## 3. Database Modules

Each module below is a Postgres schema. Responsibility descriptions are intentionally identical in substance to `TRADEOS_DOMAIN_MODEL.md` Section 4 and `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3 — this document does not get to redefine what a module is responsible for, only how that responsibility is stored.

| Schema | Responsibility |
|---|---|
| `identity` | Who the user is. Authentication credentials. |
| `preferences` | Theme, language, notification settings. Zero business logic. |
| `configuration` | The versionable source of truth for the Evaluation Engine's criteria and weights, and the shared reference catalogs (Setups, Sessions, Strategies, Entry Triggers, and the **canonical Mistake taxonomy** — categories, tag names, and descriptive metadata; see Section 3.1). |
| `trading` | The Trade aggregate and everything transactionally owned by it: its Checklist Snapshot, its Evaluation Snapshot (and that snapshot's criterion-level breakdown), and its tagged Mistakes. |
| `playbook` | Setup definitions (entry/exit criteria, risk rules) and their attachments. Performance numbers are never stored here (Section 3.1). |
| `journal` | Free-text qualitative reflection, trade-scoped or period-scoped. |
| `platform` | Cross-cutting concerns with no business meaning of their own — currently, only the event log (Section 2.7). |

### 3.1 Three Modules Deliberately Have No Tables

- **`evaluation`** — the Evaluation Engine is a pure domain service (`TRADEOS_DOMAIN_MODEL.md` Section 12.1: "a pure function of its inputs... holds no state of its own"). It reads `configuration`'s criteria/weights and `trading`'s Checklist Snapshot, and writes its result into `trading.evaluation_snapshots` (Section 3.1.1 below explains why that table lives in `trading`, not `evaluation`). There is nothing for an `evaluation` schema to persist.
- **`analytics`** — by explicit Domain Model decision (KDD-04), Analytics owns no data of its own; it recomputes on demand from `trading`. It has no schema.
- **`mistake_tracking`** — **confirmed ownership split (resolves the tension previously noted between Domain Model Sections 4.3 and 4.6; see Section 14's Resolved Decisions Log):** `configuration` owns the **canonical mistake taxonomy** — the categories, tag names, and any descriptive metadata about a mistake tag (Section 6.8). `mistake_tracking` owns **only analytical/statistical information derived from Trades** — frequency, cost, and priority ranking, computed by reading `trading.trade_mistakes` and `configuration.catalog_entries` (kind=`mistake_tag`). It stores none of that derived information either (the same "recompute on demand" posture as Analytics, Domain Model KDD-04) — it has no schema, because there is nothing about a mistake tag's *identity* for it to own, only read-side computation over facts owned elsewhere.

#### 3.1.1 Why `evaluation_snapshots` and `checklist_snapshots` Live in `trading`, Not `evaluation`

This is worth stating explicitly because it is easy to expect otherwise. `TRADEOS_DOMAIN_MODEL.md` Section 6 (KDD-02) and Section 8.2 are explicit: `EvaluationSnapshot` and `ChecklistSnapshot` are **owned by the Trade aggregate**, with no independent lifecycle. `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4 additionally requires the Trade, its Checklist Snapshot, and its Evaluation Snapshot to be persisted together, in one transaction. A single atomic transaction across two Postgres schemas is fully supported by Postgres (schemas are a namespacing tool, not a transactional boundary), so this is not a technical constraint — but placing all three tables in the schema of the aggregate that owns them (`trading`) keeps "which schema do I look in to find everything about a Trade" unambiguous, which the alternative (splitting them across `trading` and `evaluation`) would not. The *code* that computes the values still lives in the `evaluation` module (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 7) — this is a case where data ownership (storage) and behavior ownership (computation) are deliberately different, and that difference is itself the point of Clean Architecture's separation of concerns.

### 3.2 On the Prompt's Example Modules (AI, Reporting, Notifications, Calendar)

Per `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 13 and `TRADEOS_DOMAIN_MODEL.md` Section 17 (Future Reserved Domains), **AI, Reporting, and Notifications are reserved schema namespaces with zero tables today** (Section 12) — inventing their tables now, before their domain entities exist in any frozen document, would violate this document's own mandate not to invent business logic. **"Calendar" is not a named Bounded Context or Future Reserved Domain in any frozen document.** Rather than silently absorbing it into an existing schema or inventing a new one, this is flagged as **Open Question DB-1** (Section 14): does "Calendar" refer to a calendar-style *view* of existing Trade/Journal data (which would need no new tables at all — it would be a frontend presentation of `trading.trades` and `journal.journal_entries` grouped by date), or a genuinely new entity (e.g., a trading-day plan or economic calendar)? This document takes no position until the Domain Model is amended to answer it.

---

## 4. Entity-to-Table Mapping

Every entity named in `TRADEOS_DOMAIN_MODEL.md` Sections 7–8, mapped to its table(s).

| Domain Model Entity | Table(s) | Purpose | Ownership | Lifecycle | Primary Key |
|---|---|---|---|---|---|
| Trade (Aggregate Root) | `trading.trades` | The core record of one trading decision | Owns its own Checklist/Evaluation Snapshots and Mistake references | Open → Closed; soft-deletable | `id` UUID |
| ChecklistSnapshot | `trading.checklist_snapshots` | Pre-trade context capture | Owned by Trade (1:1) | Created once, immutable | `id` UUID |
| EvaluationSnapshot | `trading.evaluation_snapshots` | The 5 engines' scores for one Trade | Owned by Trade (1:1) | Created once, immutable; superseded (not overwritten) on re-evaluation | `id` UUID |
| CriterionBreakdownRow (Value Object) | `trading.evaluation_snapshot_breakdowns` | One line of a Score's explanation | Owned by EvaluationSnapshot (1:many) | Created once with its parent, immutable | `id` UUID |
| ScoringCriterion | `configuration.scoring_criteria` | Definition of one measurable input to one Engine | Owned by ScoringConfiguration | Created; deactivatable, never deleted | `id` VARCHAR (Section 2.4.1) |
| ScoringWeight | `configuration.scoring_weights` | How much one Criterion counts, per Profile, per config version | Owned by ScoringConfiguration | Versioned (Section 9) | `id` UUID |
| ScoringConfiguration (Aggregate Root) | `configuration.scoring_configuration_versions` | The versioned, complete set of Criteria/Weights | Owns its ScoringWeight rows for that version | Published; superseded, never edited | `id` UUID |
| EngineType (Enum, extensible) | `configuration.engine_types` | The set of Evaluation Engines that exist | Referenced by ScoringCriterion, EvaluationSnapshot rows | Rows added as new engines are introduced (Section 7) | `code` VARCHAR |
| ScoringProfile (Enum, extensible) | `configuration.scoring_profiles` | The set of trading profiles | Referenced by ScoringWeight | Rows added as new profiles are introduced | `code` VARCHAR |
| Catalog / CatalogEntry | `configuration.catalog_entries` | Setups, Sessions, Strategies, Entry Triggers, Mistake Tags | Referenced by Trade | Deactivatable, never deleted | `id` UUID |
| PlaybookSetup (Aggregate Root) | `playbook.playbook_setups` | Living definition of one trading setup | References a `catalog_entries` (kind=setup) row | Active ⇄ Deprecated | `id` UUID |
| (Playbook attachments — implied by Domain Model 8.8's "example references") | `playbook.playbook_setup_attachments` | Screenshots/examples for a setup | Owned by PlaybookSetup | Added/removed freely (presentation content, not history) | `id` UUID |
| MistakeTag (CatalogEntry specialization) | `configuration.catalog_entries` (kind=`mistake_tag`) | One named error category | Referenced by Trade via junction | Deactivatable, never deleted | `id` UUID |
| (Trade↔Mistake relationship) | `trading.trade_mistakes` | Many-to-many junction | Owned by Trade | Rows added/removed as tags change on an open Trade; frozen once Trade is Closed (Section 9) | composite `(trade_id, catalog_entry_id)` |
| JournalEntry (Aggregate Root) | `journal.journal_entries` | Free-text reflection | References Trade OR a date range | Created; editable; soft-deletable | `id` UUID |
| UserAccount (Aggregate Root, Generic) | `identity.user_accounts` | User identity | — | Created; rarely deleted | `id` UUID |
| UserPreferences (Aggregate Root, Generic) | `preferences.user_preferences` | Theme/language/notifications | 1:1 with UserAccount | Created with account; edited freely | `id` UUID |

---

## 5. Relationship Diagram

Described in prose (per this document's "no SQL yet" mandate) rather than as a literal ERD image, organized by relationship type.

### 5.1 One-to-One
- `trading.trades` ↔ `trading.checklist_snapshots` — a Trade has exactly one Checklist Snapshot. Enforced by a `UNIQUE` constraint on `checklist_snapshots.trade_id`.
- `trading.trades` ↔ `trading.evaluation_snapshots` — a Trade has exactly one *current* Evaluation Snapshot at any time (Section 9 explains how re-evaluation is handled without violating this). Enforced by a partial `UNIQUE` constraint (Section 6.12).
- `identity.user_accounts` ↔ `preferences.user_preferences` — one set of preferences per user. Enforced by `UNIQUE` on `user_preferences.user_id`.
- `configuration.catalog_entries` (kind=setup) ↔ `playbook.playbook_setups` — a Playbook Setup elaborates exactly one catalog Setup entry. Enforced by `UNIQUE` on `playbook_setups.catalog_entry_id`.

### 5.2 One-to-Many
- `trading.evaluation_snapshots` → `trading.evaluation_snapshot_breakdowns` — one snapshot has many breakdown rows (one per criterion, per engine, that contributed).
- `configuration.scoring_configuration_versions` → `configuration.scoring_weights` — one configuration version has many weight rows.
- `configuration.scoring_criteria` → `configuration.scoring_weights` — one criterion is weighted across many (version, profile) combinations.
- `identity.user_accounts` → `trading.trades` — one user has many trades (today, exactly one user has all of them — Section 2.7).
- `trading.trades` → `journal.journal_entries` — one Trade may have many trade-scoped journal entries (the Domain Model does not limit this to one).
- `playbook.playbook_setups` → `playbook.playbook_setup_attachments` — one setup has many attachments.

### 5.3 Many-to-Many
- `trading.trades` ↔ `configuration.catalog_entries` (kind=`mistake_tag`) — via the `trading.trade_mistakes` junction table. A Trade may reference many Mistake Tags; a Mistake Tag applies to many Trades.

### 5.4 Reference (Many-to-One), Not Ownership
These are the relationships Domain Model Section 8.1 describes as "references (does not own)":
- `trading.trades.strategy_id` → `configuration.catalog_entries` (kind=strategy)
- `trading.trades.setup_id` → `configuration.catalog_entries` (kind=setup)
- `trading.trades.session_id` → `configuration.catalog_entries` (kind=session)
- `trading.trades.entry_trigger_id` → `configuration.catalog_entries` (kind=entry_trigger)

All four are **nullable** foreign keys — Domain Model Section 8.1 explicitly allows a Trade to exist with some classification fields unset. All four use `ON DELETE RESTRICT` semantics conceptually, but because `catalog_entries` rows are never hard-deleted (Section 2.6), this is enforced by *application logic preventing deletion* rather than ever needing the database's `ON DELETE` behavior to fire.

### 5.5 Aggregate Ownership Boundary (Not a Foreign Key Relationship, but a Rule)

The `trading` schema's tables (`trades`, `checklist_snapshots`, `evaluation_snapshots`, `evaluation_snapshot_breakdowns`, `trade_mistakes`) may only ever be written to through the `trading` module's repository — this is not expressible as a database constraint, but is the direct storage-level consequence of `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 3.3 (Forbidden Dependencies) and is enforced by Postgres role/grant permissions (Section 11) restricting which application-level database role may `INSERT`/`UPDATE` each schema.

---

## 6. Table Specifications

Every table, fully specified. "Historical behavior" states what happens to existing rows when related data changes — the section most directly responsible for this document's mandate that historical data never silently changes.

### 6.1 `identity.user_accounts`
- **Purpose:** the identity of a person using TradeOS.
- **Primary Key:** `id UUID`.
- **Columns:** `email VARCHAR(255) NOT NULL`, `password_hash VARCHAR(255) NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **Unique Constraints:** `email`.
- **Check Constraints:** none beyond `NOT NULL`.
- **Indexes:** unique index on `email` (needed for login lookups).
- **Historical Behavior:** not versioned; a password change updates the row in place (a password is not a historical fact worth preserving — the opposite of, e.g., a Trade's price).

### 6.2 `preferences.user_preferences`
- **Purpose:** theme, language, notification preferences.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `user_id UUID NOT NULL REFERENCES identity.user_accounts(id)`.
- **Columns:** `theme VARCHAR(20) NOT NULL DEFAULT 'dark'`, `language VARCHAR(10) NOT NULL DEFAULT 'es'`, `notification_settings JSONB NOT NULL DEFAULT '{}'`, `created_at`, `updated_at`.
- **Unique Constraints:** `user_id` (enforces the 1:1 relationship, Section 5.1).
- **Historical Behavior:** none — always reflects current preference, never versioned.

### 6.3 `configuration.engine_types`
- **Purpose:** the extensible set of Evaluation Engines. **This table is the schema-level mechanism that lets a sixth engine be added as a data row, never a migration.**
- **Primary Key:** `code VARCHAR(30)` (e.g., `'confidence'`, `'quality'`, `'execution'`, `'market_context'`, `'bias'`) — a natural key, for the same reasoning as Section 2.4.1.
- **Columns:** `display_name VARCHAR(60) NOT NULL`, `is_signed BOOLEAN NOT NULL` (realizes Domain Invariant DI-05 — exactly one row, `bias`, has `is_signed = true`), `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`.
- **Check Constraints:** application-level rule (not a database CHECK, since it spans rows) that at most one active row may have `is_signed = true` **unless** a documented Key Domain Decision explicitly permits a second signed engine (Domain Model DI-05) — flagged here as an application-layer invariant rather than a database CHECK because Postgres cannot express "at most one row matching a condition" as a simple column constraint without a partial unique index trick; a partial unique index on `is_signed` where `is_signed = true AND is_active = true` is the concrete mechanism (Section 6.3.1).
- **Historical Behavior:** rows are never deleted, only deactivated — an `EvaluationSnapshot` referencing a since-deactivated engine type must remain fully meaningful.

#### 6.3.1 Note on the Partial Unique Index
`CREATE UNIQUE INDEX ... ON engine_types (is_signed) WHERE is_signed = true AND is_active = true` is the mechanism referenced above — described here in prose per this document's no-SQL mandate, and left for the implementing engineer to express in the actual migration.

### 6.4 `configuration.scoring_profiles`
- **Purpose:** the extensible set of trading profiles (Day Trading, Swing Trading, Scalping, and any future profile).
- **Primary Key:** `code VARCHAR(30)`.
- **Columns:** `display_name VARCHAR(60) NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`.
- **Historical Behavior:** same as `engine_types` — deactivate, never delete.

### 6.5 `configuration.scoring_criteria`
- **Purpose:** definition of one measurable input to one Engine.
- **Primary Key:** `id VARCHAR(64)` (Section 2.4.1).
- **Foreign Keys:** `engine_type_code VARCHAR(30) NOT NULL REFERENCES configuration.engine_types(code)`.
- **Columns:** `category VARCHAR(64) NULL`, `name VARCHAR(120) NOT NULL`, `description TEXT NOT NULL DEFAULT ''`, `source_field VARCHAR(64) NOT NULL`, `min_value NUMERIC NOT NULL`, `max_value NUMERIC NOT NULL`, `category_map JSONB NULL` (holds the label→sub-score lookup for categorical criteria, e.g., `{"Full Alignment": 100, "Partial Conflict": 40}`), `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`, `updated_at`.
- **Check Constraints:** `max_value >= min_value`.
- **Indexes:** index on `engine_type_code` (every score calculation filters criteria by engine).
- **Historical Behavior:** deactivated, never deleted (Domain Model Section 8.4) — an `EvaluationSnapshot` created while a criterion was active remains fully explainable via `evaluation_snapshot_breakdowns` even after the criterion is later deactivated, because the breakdown row stores the criterion's *name and values at the time*, not merely a live-dereferenced pointer (Section 6.13).

### 6.6 `configuration.scoring_configuration_versions`
- **Purpose:** the Aggregate Root binding a complete, internally-consistent set of criteria/weights together as one named, immutable version.
- **Primary Key:** `id UUID`.
- **Columns:** `version_label VARCHAR(40) NOT NULL` (e.g., `"v1.3"`, human-assigned or auto-generated), `status VARCHAR(20) NOT NULL` (`draft` | `published` | `superseded`), `published_at TIMESTAMPTZ NULL`, `created_at`, `created_by_user_id UUID NULL REFERENCES identity.user_accounts(id)`.
- **Unique Constraints:** `version_label`.
- **Check Constraints:** `status IN ('draft','published','superseded')`; `published_at IS NOT NULL WHEN status != 'draft'`.
- **Historical Behavior:** **never updated once `published`.** A change to weights or criteria participation creates a *new* `scoring_configuration_versions` row (with its own new `scoring_weights` rows); the prior version's `status` transitions to `superseded`, and it is retained forever, unedited. This is the direct schema-level implementation of Domain Invariant DI-06/DI-07.

### 6.7 `configuration.scoring_weights`
- **Purpose:** how much one Criterion counts, for one Profile, within one Configuration Version.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `configuration_version_id UUID NOT NULL REFERENCES configuration.scoring_configuration_versions(id)`, `criterion_id VARCHAR(64) NOT NULL REFERENCES configuration.scoring_criteria(id)`, `profile_code VARCHAR(30) NOT NULL REFERENCES configuration.scoring_profiles(code)`.
- **Columns:** `weight NUMERIC NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`.
- **Unique Constraints:** `(configuration_version_id, criterion_id, profile_code)` — a criterion has at most one weight per profile, per version.
- **Check Constraints:** `weight >= 0`.
- **Indexes:** composite index on `(configuration_version_id, profile_code)` — this is the exact lookup the Evaluation Engine performs on every scoring operation (fetch all active weights for the current version and profile), and is the single most performance-sensitive query in the schema (Section 10).
- **Historical Behavior:** immutable once its parent version is published, per Section 6.6.

### 6.8 `configuration.catalog_entries`
- **Purpose:** the shared reference lists — Setups, Sessions, Strategies, Entry Triggers, and Mistake Tags. **Confirmed:** this table is the sole, canonical home of the mistake taxonomy — its categories (via `kind`), tag names, and descriptive metadata. `mistake_tracking` (Section 3.1) never duplicates or shadows any of this; it only reads it. "Catalog" (Domain Model Section 8.7) is a logical grouping realized here as a `kind` column, not a separate parent table — there is no business meaning to a `catalogs` table with zero columns of its own beyond "which kind," so it is not created (Architectural Principle 4).
- **Primary Key:** `id UUID`.
- **Columns:** `kind VARCHAR(20) NOT NULL` (`setup` | `session` | `strategy` | `entry_trigger` | `mistake_tag`), `name VARCHAR(120) NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`, `updated_at`. **Note:** `name`, `kind`, and `is_active` are, today, the complete confirmed shape of a mistake tag's "categories, tags, metadata." If a richer metadata need emerges later (e.g., a free-text description, or a sub-grouping within `mistake_tag`), it is an additive column on this same table — never a reason to give `mistake_tracking` a schema of its own, since the ownership boundary (Configuration = identity/metadata, Mistake Tracking = derived analytics only) does not depend on how many descriptive fields a tag carries.
- **Unique Constraints:** `(kind, name)` — prevents two active *or inactive* entries of the same kind sharing a name, avoiding the exact Excel defect `PROJECT_AUDIT.md` documented (category names drifting out of sync).
- **Check Constraints:** `kind IN ('setup','session','strategy','entry_trigger','mistake_tag')`.
- **Indexes:** index on `kind` (every catalog lookup filters by kind).
- **Historical Behavior:** deactivated, never deleted (Domain Invariant DI-10); a Trade referencing a deactivated entry remains fully valid (Section 5.4).

### 6.9 `trading.trades` *(v2.0 — see Domain Model KDD-07)*
- **Purpose:** the Trade aggregate root.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `user_id UUID NOT NULL REFERENCES identity.user_accounts(id)`, `strategy_id UUID NULL REFERENCES configuration.catalog_entries(id)`, `setup_id UUID NULL REFERENCES configuration.catalog_entries(id)`, `session_id UUID NULL REFERENCES configuration.catalog_entries(id)`, `entry_trigger_id UUID NULL REFERENCES configuration.catalog_entries(id)`.
- **Columns:** `market VARCHAR(20) NOT NULL`, `direction VARCHAR(5) NOT NULL` (`long`|`short`), `status VARCHAR(10) NOT NULL DEFAULT 'open'` (`planned`|`open`|`closed`, **new in v2.0**), `entry_price NUMERIC NULL` (**relaxed from `NOT NULL` in v2.0** — absent while `status='planned'`), `stop_loss NUMERIC NULL` (**relaxed from `NOT NULL`**, same reason), `take_profit NUMERIC NULL` (**new in v2.0**), `exit_price NUMERIC NULL`, `size NUMERIC NOT NULL DEFAULT 0`, `margin_used NUMERIC NULL` (**new in v2.0** — distinct from `size`; the Excel keeps `Tamaño`/`Size` and `Margin` as two separate columns), `leverage VARCHAR(10) NOT NULL DEFAULT ''`, `result VARCHAR(5) NULL` (**relaxed from `NOT NULL DEFAULT 'open'`** — `tp`|`sl`|`be` only in v2.0; `NULL` while not `Closed`, replacing the retired `'open'` value), `realized_pnl NUMERIC NOT NULL DEFAULT 0`, `mfe_price NUMERIC NULL`, `mae_price NUMERIC NULL`, `notes TEXT NOT NULL DEFAULT ''`, `entered_at TIMESTAMPTZ NULL` (**relaxed from `NOT NULL` in v2.0**, same `planned` reason), `closed_at TIMESTAMPTZ NULL`, `created_at`, `updated_at`, `deleted_at TIMESTAMPTZ NULL`, `created_by_user_id UUID NULL REFERENCES identity.user_accounts(id)`.
- **Explicitly absent columns:** `r_multiple`, `mfe_r`, `mae_r`, `captured_pct`, `potential_left_r` — **never stored** (unchanged from v1.1). **`roi_percent`/`pnl_percent` are likewise deliberately absent** (Domain Model KDD-07, DI-14, decided explicitly in the same v2.0 review that added `take_profit`/`margin_used`) — both are computed at query time from `realized_pnl`/`margin_used`/`leverage` (`roi_percent = realized_pnl / margin_used`; `pnl_percent = roi_percent / leverage`, the Excel's own literal formula). These are computed properties (Domain Model Section 8.1) derived at query or application time. Storing any of them would recreate precisely the class of defect `PROJECT_AUDIT.md` found repeatedly in the Excel — a derived value silently drifting from the facts that produce it.
- **Check Constraints:** `direction IN ('long','short')`; `status IN ('planned','open','closed')` (**new in v2.0**); `result IS NULL OR result IN ('tp','sl','be')` (**redefined in v2.0** — `'open'` retired as a `result` value, see `status` instead); `entry_price IS NULL OR stop_loss IS NULL OR (direction = 'long' AND stop_loss < entry_price) OR (direction = 'short' AND stop_loss > entry_price)` (INV-TRADE-01, **now conditional on both prices existing**); a **redefined** INV-TRADE-02 realized as: `(status='planned' AND entry_price IS NULL AND stop_loss IS NULL AND entered_at IS NULL AND exit_price IS NULL AND closed_at IS NULL AND result IS NULL) OR (status='open' AND entry_price IS NOT NULL AND entered_at IS NOT NULL AND exit_price IS NULL AND closed_at IS NULL AND result IS NULL) OR (status='closed' AND entry_price IS NOT NULL AND entered_at IS NOT NULL AND exit_price IS NOT NULL AND closed_at IS NOT NULL AND result IS NOT NULL)`.
- **Indexes:** `user_id` (every query is scoped to a user); `entered_at` (Analytics' time-based queries — a partial index, `WHERE entered_at IS NOT NULL`, since v2.0 allows it to be absent for `planned` rows and Analytics never reads those, Domain Invariant DI-13); composite `(strategy_id, setup_id, session_id, direction)` (Analytics' by-dimension grouping, Domain Model Section 12.2); partial index on `deleted_at IS NULL` (nearly every query excludes soft-deleted rows).
- **Historical Behavior:** `entered_at`, `entry_price`, `stop_loss`, `direction` are corrected only via an explicit amendment path that is itself logged to `platform.event_log` as a `TradeAmended` event (Domain Model Section 11) — the row is updated in place (there is no `trades_history` table, Section 9 explains why this is an acceptable, documented choice) but the fact that an amendment occurred is never silently lost. **New in v2.0:** the `planned → open` transition is its own explicit, logged action (`TradeOpened`, analogous to `TradeClosed`), never an implicit side effect of an unrelated `PATCH`.

### 6.10 `trading.checklist_snapshots`
- **Purpose:** the pre-trade context capture.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `trade_id UUID NOT NULL REFERENCES trading.trades(id)`.
- **Columns:** `answers JSONB NOT NULL` — a flexible map of `{criterion_source_field: raw_value}` (e.g., `{"htf_alignment": "Full Alignment", "bias_index": 45}`). **This is deliberately JSONB, not one column per checklist question**, because the set of checklist questions is exactly the set of active `scoring_criteria` — which is config-driven and must be extensible without a schema migration (this document's Section 1, Goal 3). `created_at`.
- **Unique Constraints:** `trade_id` (enforces the 1:1 relationship).
- **Historical Behavior:** immutable once written (Domain Model Section 8.3) — never edited, even if the trader later believes conditions were different than recorded.

### 6.11 `configuration` Reference from `checklist_snapshots.answers`
Not a physical foreign key (JSONB keys cannot carry a database-enforced foreign key), but an **application-level invariant**: every key in `answers` must correspond to an existing `scoring_criteria.source_field` value at the time of writing. This is validated by the `evaluation` module at scoring time, not by a database constraint — a deliberate, documented tradeoff of flexibility (Section 1, Goal 3) over database-level enforcement, acceptable because Correctness here is protected by the Evaluation Engine's own test suite (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8, testing row) rather than the schema.

### 6.12 `trading.evaluation_snapshots`
- **Purpose:** the immutable record of what all five Engines scored for one Trade.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `trade_id UUID NOT NULL REFERENCES trading.trades(id)`, `configuration_version_id UUID NOT NULL REFERENCES configuration.scoring_configuration_versions(id)` (records exactly which configuration version produced this snapshot — the specific mechanism behind Domain Invariant DI-06/DI-07's reproducibility guarantee).
- **Columns:** `confidence_score NUMERIC NULL`, `confidence_grade VARCHAR(2) NULL`, `quality_score NUMERIC NULL`, `quality_grade VARCHAR(2) NULL`, `execution_score NUMERIC NULL`, `execution_grade VARCHAR(2) NULL`, `market_context_score NUMERIC NULL`, `market_context_grade VARCHAR(2) NULL`, `bias_score NUMERIC NULL` (signed, Domain Invariant DI-05 — **no `bias_grade` column**, since a directional score does not map to a quality grade, per Domain Model Section 2.2's definition of Bias), `is_current BOOLEAN NOT NULL DEFAULT true`, `created_at`.
- **Unique Constraints:** partial unique index on `trade_id WHERE is_current = true` — enforces "exactly one *current* snapshot per Trade" (Section 5.1) while still permitting multiple historical rows per Trade after re-evaluation.
- **Historical Behavior:** **never updated or deleted.** A "recalculate historical trades" action (`TRADEOS_DOMAIN_MODEL.md` Section 8.2) inserts a **new** row with `is_current = true` and flips the previous row's `is_current` to `false` — both remain in the table permanently. This is the schema-level mechanism realizing "old snapshot retained as history, not overwritten."

### 6.13 `trading.evaluation_snapshot_breakdowns`
- **Purpose:** the per-criterion explanation behind a Score — the mechanism satisfying Domain Invariant DI-08 ("every Score must be explainable").
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `evaluation_snapshot_id UUID NOT NULL REFERENCES trading.evaluation_snapshots(id)`, `criterion_id VARCHAR(64) NOT NULL REFERENCES configuration.scoring_criteria(id)`.
- **Columns:** `engine_type_code VARCHAR(30) NOT NULL REFERENCES configuration.engine_types(code)`, `criterion_name_at_time VARCHAR(120) NOT NULL` (a **copy** of the criterion's name at scoring time — see reasoning below), `raw_value TEXT NOT NULL` (stored as text because a raw value may be numeric or categorical; the application interprets it), `normalized_value NUMERIC NOT NULL`, `weight NUMERIC NOT NULL`, `contribution NUMERIC NOT NULL`, `created_at`.
- **Why `criterion_name_at_time` is a deliberate, documented denormalization:** Section 10 covers this schema's general normalization stance, but this is the one explicit exception. If `scoring_criteria.name` were changed later (a rename, not a deactivation), a purely-normalized design (reading the name live via the foreign key) would silently rewrite how a historical Score is explained — violating this document's Goal 1 more directly than the storage cost of a denormalized copy is worth. The `criterion_id` foreign key is retained for querying and integrity; `criterion_name_at_time` is retained for historical fidelity. Both exist; they answer different questions.
- **Historical Behavior:** immutable, forever, exactly as its parent `evaluation_snapshots` row.

### 6.14 `trading.trade_mistakes`
- **Purpose:** many-to-many junction between Trade and Mistake Tag.
- **Primary Key:** composite `(trade_id, catalog_entry_id)`.
- **Foreign Keys:** `trade_id UUID NOT NULL REFERENCES trading.trades(id)`, `catalog_entry_id UUID NOT NULL REFERENCES configuration.catalog_entries(id)`.
- **Check Constraints:** application-level (not database-level, since it requires a cross-table lookup) rule that `catalog_entry_id` must reference a row with `kind = 'mistake_tag'`.
- **Columns:** `created_at`.
- **Historical Behavior:** rows may be added or removed while the Trade is `Open`; once `Closed`, the application should treat further changes as significant enough to log (not blocked at the database level, but a documented expectation for the application layer — see Open Question DB-2, Section 14).

### 6.15 `playbook.playbook_setups`
- **Purpose:** the living definition of one trading setup.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `catalog_entry_id UUID NOT NULL REFERENCES configuration.catalog_entries(id)`.
- **Columns:** `entry_criteria TEXT NOT NULL DEFAULT ''`, `exit_criteria TEXT NOT NULL DEFAULT ''`, `ideal_conditions TEXT NOT NULL DEFAULT ''`, `risk_rules TEXT NOT NULL DEFAULT ''`, `status VARCHAR(20) NOT NULL DEFAULT 'active'` (`active`|`deprecated`), `created_at`, `updated_at`, `deleted_at TIMESTAMPTZ NULL`.
- **Unique Constraints:** `catalog_entry_id` (1:1 with its Setup catalog entry).
- **Check Constraints:** `status IN ('active','deprecated')`.
- **Explicitly absent columns:** any performance metric (win rate, expectancy) — always a live read from Analytics (Domain Model Section 8.8), never stored here.
- **Historical Behavior:** edited freely in place — a Playbook Setup's definition is documentation, not a historical fact whose past values need preserving (unlike a Trade's price). If setup-definition version history is wanted later, it is an additive table (Domain Model Section 8.8, Future Evolution), not a redesign.

### 6.16 `playbook.playbook_setup_attachments`
- **Purpose:** screenshots/examples for a setup.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `playbook_setup_id UUID NOT NULL REFERENCES playbook.playbook_setups(id)`.
- **Columns:** `file_reference VARCHAR(500) NOT NULL` (a URL or object-storage key — the actual file lives in object storage, never in Postgres, per standard practice; this schema stores only the reference), `caption VARCHAR(255) NOT NULL DEFAULT ''`, `created_at`.
- **Historical Behavior:** freely added/removed; presentation content, not history.

### 6.17 `journal.journal_entries`
- **Purpose:** free-text qualitative reflection.
- **Primary Key:** `id UUID`.
- **Foreign Keys:** `user_id UUID NOT NULL REFERENCES identity.user_accounts(id)`, `trade_id UUID NULL REFERENCES trading.trades(id)`.
- **Columns:** `content TEXT NOT NULL`, `period_start DATE NULL`, `period_end DATE NULL`, `created_at`, `updated_at`, `deleted_at TIMESTAMPTZ NULL`.
- **Check Constraints:** exactly one of (`trade_id IS NOT NULL`) or (`period_start IS NOT NULL AND period_end IS NOT NULL`) must hold, never both, never neither — the direct schema realization of Domain Model Section 8.10 ("either a Trade reference or a date-range reference, never both").
- **Indexes:** `trade_id`; `(period_start, period_end)`.
- **Historical Behavior:** editable in place (a journal entry is the trader's own evolving reflection, not an immutable fact) — but soft-deletable, never hard-deleted.

### 6.18 `platform.event_log`
- **Purpose:** durable record of every Domain Event (`TRADEOS_DOMAIN_MODEL.md` Section 11) as it fires — the storage-level implementation of Architectural Principle 5 (Observability Is Not Optional).
- **Primary Key:** `id UUID`.
- **Columns:** `event_type VARCHAR(60) NOT NULL` (`TradeRegistered`, `TradeEvaluated`, `TradeClosed`, `TradeAmended`, `MistakeTagged`, `ScoringConfigurationChanged`, `PlaybookSetupUpdated`, `CatalogEntryDeactivated`), `aggregate_type VARCHAR(60) NOT NULL` (which kind of entity the event is about, e.g., `Trade`), `aggregate_id UUID NOT NULL` (the specific entity's ID — deliberately **not** a foreign key, since the referenced row may later be in a different schema than the event log expects, and an event must remain readable even if its subject is later soft-deleted), `payload JSONB NOT NULL` (the event's data, shaped per Domain Model Section 11's description of what each event means), `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **Indexes:** `(aggregate_type, aggregate_id)`; `event_type`; `occurred_at`.
- **Historical Behavior:** append-only, forever. Never updated, never deleted — this table's entire value is being an unmodifiable record of what happened and when.

---

## 7. Evaluation Engine Storage

This is the most important section of this document, per the prompt's own instruction, and it consolidates decisions already made piecemeal in Section 6 into one coherent explanation of how the five requirements are satisfied.

### 7.0 Confirmed Decision: Engines Are Stable Business Concepts, Their Configuration Is Data

**This is a confirmed architectural decision, not a tentative design choice:**

- **The set of five Evaluation Engines (Confidence, Quality, Execution, Market Context, Bias) is treated as a stable business concept** — it is realized as explicit, named columns on `trading.evaluation_snapshots` (`confidence_score`, `quality_score`, etc., Section 6.12), not as a fully generic per-engine child table. This is deliberate: these five engines are a settled part of the Domain Model (`TRADEOS_DOMAIN_MODEL.md` Section 8.1) and Product Bible (Section 8), read together on nearly every access, and do not benefit from being modeled as if they might be arbitrary or interchangeable at the schema level.
- **Everything about how each engine computes its score is fully data-driven** — the criteria it reads (`configuration.scoring_criteria`), how much each counts (`configuration.scoring_weights`), which profiles it supports (`configuration.scoring_profiles`), and which configuration version was in effect for any historical calculation (`configuration.scoring_configuration_versions`). None of this requires a schema change to evolve, ever (Sections 7.3–7.5).
- **Introducing a sixth engine is an additive migration, never a generic redesign.** Concretely, it requires:
  1. One new row in `configuration.engine_types` (a data change, not a migration).
  2. New `configuration.scoring_criteria` and `configuration.scoring_weights` rows for that engine (data changes).
  3. One new nullable column pair (`<engine>_score`, `<engine>_grade`, unless the new engine is signed like Bias, in which case no grade column) added to `trading.evaluation_snapshots` — an additive, backward-compatible schema migration (Section 13.2) that does not touch, rename, or reinterpret any existing column.
  4. No change whatsoever to `trading.evaluation_snapshot_breakdowns`, which is already fully generic per criterion and per engine (Section 6.13) and requires nothing new to support the sixth engine's breakdown rows.

This asymmetry — criteria/weights/profiles are pure data, the five-engine set is a schema-stable concept extended additively — is the intended design, not a compromise. It reflects that *what a criterion measures* changes often (the entire reason Config-Driven Criteria exists, Product Bible Section 8.2), while *how many engines exist* changes rarely, and treating both as equally fluid would add a generic-table indirection cost to the far more common, everyday operation (reading a Trade's five scores together) to protect against a rare event (adding a sixth engine) that, when it happens, costs one small additive migration in exchange.

### 7.1 "Five independent engines" 
Realized by `configuration.engine_types` (Section 6.3) being a **data table, not a hardcoded enum or a set of five parallel table structures.** `trading.evaluation_snapshots` has one column-pair (score/grade) per currently-known engine (Section 6.12) rather than a fully generic `evaluation_scores` child table with one row per engine — this is a deliberate, bounded exception to "everything about engines is data-driven," justified in Section 7.5.

### 7.2 "Versioned configurations"
Realized by `configuration.scoring_configuration_versions` (Section 6.6) being append-only: a "change" is always a new version row, never an edit to an existing one, with `status` tracking which version is currently live.

### 7.3 "Criteria"
Realized by `configuration.scoring_criteria` (Section 6.5) — one row per measurable input, referencing `engine_types` and carrying its own normalization range and (optional) category map, exactly matching Domain Model Section 8.4.

### 7.4 "Weights"
Realized by `configuration.scoring_weights` (Section 6.7) — the join between a criterion, a profile, and a configuration version, carrying the numeric weight and an `is_active` flag (the schema-level realization of Domain Invariant INV-WEIGHT-01's "sum of active weights only" rule, computed at query time by the application, never pre-aggregated in the schema).

### 7.5 "Profiles"
Realized by `configuration.scoring_profiles` (Section 6.4) — a data table, not an enum, for the same "add a row, not a migration" reasoning as `engine_types`.

**Why `evaluation_snapshots` still has named columns per engine, rather than being fully generic (a child table with one row per engine per snapshot, mirroring `evaluation_snapshot_breakdowns`'s shape):** a fully generic design was considered and rejected for the *snapshot's own score*, specifically (not for its breakdown, which *is* fully generic, Section 6.13). The reasoning: an `EvaluationSnapshot`'s five scores are read together, on almost every access (a Trade Detail view shows all five at once, per `TradeOS_UI_v3`'s reference frontend), and Domain Invariant DI-05 hardcodes that there are exactly five engines *today*, with Bias uniquely signed — a fully generic table would require a runtime pivot on every single read to reconstruct that familiar shape. If a sixth engine is added, it is one new nullable column added to `evaluation_snapshots` (a backward-compatible schema migration, not a redesign — Section 13) — a deliberately different, and lighter-weight, extensibility mechanism than criteria/weights/profiles get, because the *set of engines* changes far less often than the *set of criteria within an engine*. This asymmetry is intentional and is the one place this section's "no redesign for a new engine" promise costs a (minor, additive, non-breaking) migration rather than a pure data change — documented here rather than hidden, per this document's Open Questions mandate (Section 14 registers this as an accepted, bounded exception, not an open question, since the reasoning is settled).

### 7.6 "Historical snapshots" and "Reproducible scores"
Both realized together by `evaluation_snapshots.configuration_version_id` (Section 6.12) plus `evaluation_snapshot_breakdowns` (Section 6.13): given any historical `EvaluationSnapshot`, an engineer (or the trader, via the future Rule Explorer UI concept named in `TRADEOS_PRODUCT_BIBLE.md` Principle 10) can answer, with full precision, which configuration version was in effect, which criteria contributed, what their raw and normalized values were, and what each contributed to the final score — indefinitely, even after the criteria or configuration have since changed.

---

## 8. Configuration System

Every business rule that could vary is data, not code, consistent with `TRADEOS_PRODUCT_BIBLE.md` Section 8.2's Config-Driven Criteria principle:

| Concept | Table | Notes |
|---|---|---|
| Criteria | `configuration.scoring_criteria` | Section 6.5 |
| Weights | `configuration.scoring_weights` | Section 6.7 |
| Scoring Profiles | `configuration.scoring_profiles` | Section 6.4 |
| Engine Types | `configuration.engine_types` | Section 6.3 |
| Reference Catalogs (Setup/Session/Strategy/Entry Trigger/Mistake Tag) | `configuration.catalog_entries` | Section 6.8 |
| Configuration Versions | `configuration.scoring_configuration_versions` | Section 6.6 |

**"Risk profiles" and "Application configuration"** (named in the prompt's Section 8 requirements) have **no corresponding entity in any frozen document** (`TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`). Rather than inventing tables for concepts the Domain Model does not yet define, this is registered as **Open Question DB-3** (Section 14): are "Risk Profiles" a new concept distinct from `ScoringProfile` (e.g., max risk per trade, daily loss limits — the Excel's `🚫 Errores`/Dashboard risk-rule concepts, never formally modeled in the Domain Model), or should trading-profile-specific risk rules be folded into the existing `ScoringProfile` concept? This document takes no position until the Domain Model answers it. "Application configuration" (feature flags, environment-level settings) is deliberately excluded from the business schema entirely — it belongs in environment configuration/secrets management (Section 11), not a database table, per Architectural Principle 7 (Technology Serves the Domain).

---

## 9. Historical Data Strategy

| Category | Examples | Behavior |
|---|---|---|
| **Immutable, append-only** | `checklist_snapshots`, `evaluation_snapshots`, `evaluation_snapshot_breakdowns`, `platform.event_log` | Never updated, never deleted, ever. |
| **Versioned (superseded, not edited)** | `scoring_configuration_versions` and its `scoring_weights` | A "change" always creates a new version; the old version's rows remain forever, `status` marks it superseded. |
| **Deactivatable, never deleted** | `catalog_entries`, `scoring_criteria`, `engine_types`, `scoring_profiles` | An `is_active` flag hides a row from *new* selection without affecting any existing reference to it. |
| **Mutable, soft-deletable** | `trades`, `journal_entries`, `playbook_setups` | Edited in place for non-historically-sensitive fields (e.g., a Trade's `notes`); price/direction changes on a Trade are treated as amendments (see below); `deleted_at` marks "never should have existed," not "no longer relevant." |
| **Freely mutable, no history at all** | `user_preferences`, `playbook_setup_attachments` | No business reason to preserve prior values. |

### 9.1 What Creates a Snapshot
Every Trade registration creates exactly one `checklist_snapshots` row and (at least) one `evaluation_snapshots` row, both immutable, in the same transaction as the Trade itself (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4).

### 9.2 What Creates History (Rather Than a New Snapshot)
A `TradeAmended` event (logged to `platform.event_log`) when a Trade's already-recorded facts are corrected. This document deliberately does **not** create a `trades_history` table mirroring every past state of a Trade row — the event log's `payload` JSONB captures what changed and to what, which satisfies "the amendment is never silently lost" without the schema cost of a full row-versioning table for every mutable table in the system. If a future requirement needs to reconstruct a Trade's exact state at an arbitrary past point in time (not just know that *a* change happened), that is a real gap this design accepts today — registered as **Open Question DB-4** (Section 14).

### 9.3 How Recalculation Works
"Recalculate historical trades" (an explicit, deliberate action per Domain Model Section 8.2 — never triggered automatically by a `ScoringConfigurationChanged` event) reads the Trade's `checklist_snapshots` row (unchanged) and the *new* `scoring_configuration_versions` row, runs the Evaluation Engine, and inserts a new `evaluation_snapshots` row with `is_current = true`, flipping the previous row's flag to `false`. Both rows persist. The Trade's externally-visible "current score" is always the `is_current = true` row; its full scoring history is the complete set of rows for that `trade_id`, ordered by `created_at`.

### 9.4 How Historical Scores Remain Reproducible
Answered fully in Section 7.6.

---

## 10. Performance Strategy

Per `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9's Quality Attributes Matrix, Performance is ranked 6th of 7 — this section recommends real, but conservative, provisions, and explicitly declines premature ones.

### 10.1 Indexes (Recommended Now)
- `trades`: `user_id`; `entered_at`; composite `(strategy_id, setup_id, session_id, direction)`; partial index where `deleted_at IS NULL`.
- `scoring_weights`: composite `(configuration_version_id, profile_code)`.
- `catalog_entries`: `kind`.
- `evaluation_snapshots`: partial unique on `(trade_id) WHERE is_current`.
- `journal_entries`: `trade_id`; `(period_start, period_end)`.
- `event_log`: `(aggregate_type, aggregate_id)`; `occurred_at`.

### 10.2 Composite Indexes for Analytics
Analytics' `StatisticsAggregationService` (Domain Model Section 12.2) groups by any of Strategy/Setup/Session/Direction and filters by date range — the composite index above on `trades` is sized specifically for that access pattern, following this document's Goal 6 (performance provisions follow real, known query shapes, not speculative ones).

### 10.3 Pagination
All list-style queries (trade lists, journal entries) are cursor- or offset-paginated at the API layer (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8) — this is an API concern, not a schema concern, beyond ensuring `entered_at`/`created_at` are indexed (already covered above) to make ordering cheap.

### 10.4 Partitioning
**Not recommended now.** Table partitioning (e.g., partitioning `trades` by year) is a real option once a single user's trade count is in the hundreds of thousands, far beyond the stated 20,000+ trade target (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.2). Introducing it now would violate Architectural Principle 4. **Registered as a documented future option, not a current decision.**

### 10.5 Archiving
**Not recommended now**, for the same reason as partitioning — and additionally in tension with this document's core mandate that historical data remains fully queryable, not moved to cold storage that would complicate Analytics' "recompute from source data always" guarantee (Domain Invariant DI-11).

### 10.6 Caching
**Not recommended now**, consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04 (on-demand Analytics, no materialized views in v1). If a specific, measured query proves too slow at real data volume, the `platform.event_log`'s `TradeRegistered`/`TradeEvaluated`/`TradeClosed` events (already being written, Section 6.18) are the exact mechanism a future cache-invalidation layer would need — the provision exists without the cache being built prematurely.

---

## 11. Security Considerations

Grounded in `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11, which ranked Security 5th in the Quality Attributes Matrix and explicitly deferred its deepest posture to Product Bible Open Question 3. This section covers what the schema itself must do regardless of how that question resolves.

### 11.1 Sensitive Fields
- `identity.user_accounts.password_hash` — never stores a plaintext password. Hashing algorithm/parameters are an application/implementation decision (out of scope for this document per its own mandate), but the column is explicitly named `password_hash`, not `password`, to make misuse structurally awkward.
- No API keys, broker credentials, or third-party secrets exist in this schema at all — none of the current Bounded Contexts require them (Section 13, External Integrations, remains empty). When the Broker Integration Future Reserved Domain is built, any such secret belongs in a dedicated secrets-management system, never a plain database column (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1).
- No PII beyond `email` exists in this schema today. If billing/commercial use is ever added (Product Bible Open Question 2), payment details must never be stored directly in this database — a PCI-compliant third-party processor is used instead, referenced only by an opaque token.

### 11.2 Row Ownership
Every table that should ever be scoped to a single user's data carries `user_id` (`trades`, `journal_entries`) or reaches it transitively (`checklist_snapshots`/`evaluation_snapshots` via their `trade_id`). This is the schema-level foundation for row-level security, should Product Bible Open Question 2 resolve toward multi-user — Postgres Row-Level Security (RLS) policies can be layered onto these existing columns without a schema change, only a policy addition.

### 11.3 Least-Privilege Database Roles
Consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 11.1's "a module's infrastructure layer is the only code path permitted to reach its own schema's tables": this is enforced with one Postgres role per module (e.g., a `trading_app` role with `SELECT`/`INSERT`/`UPDATE` only on the `trading` schema), rather than one superuser role the whole application shares. This is a real, recommended provision, not a premature one — it costs nothing to set up initially and directly enforces Architectural Principle 2 at the database's own permission layer, not just in application code review.

### 11.4 Encryption
- **In transit:** TLS between application and database — an infrastructure/deployment concern (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12), not a schema concern.
- **At rest:** **explicitly deferred, per Product Bible Open Question 3.** This document does not specify a standard because none has been chosen. Whatever is chosen later (e.g., Postgres Transparent Data Encryption, disk-level encryption via the hosting provider, or column-level encryption for specific sensitive fields) can be applied to this schema without redesigning it — none of the tables above assume plaintext storage as part of their logical design.

### 11.5 Audit Logging
Covered fully in Section 2.7 — `platform.event_log` is the audit mechanism this schema provides today; deeper, field-level audit is an acknowledged future option (Section 9.2, Open Question DB-4), not a current gap treated as resolved.

---

## 12. Future Scalability

How this schema accommodates each named future module **without requiring the tables above to be redesigned:**

- **AI Coaching:** per `TRADEOS_DOMAIN_MODEL.md` Section 17, this domain consumes `platform.event_log` and Analytics' output — it needs its own future `ai` schema (e.g., a table logging AI-generated observations, referencing `trades.id`/`journal_entries.id` by ID) but requires zero changes to any table in Sections 6.1–6.18. Reserved, empty today.
- **Broker Integrations:** sits upstream of `trading.trades` (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 13) — a future `integrations` schema would hold broker connection credentials (Section 11.1) and a mapping from broker-side trade IDs to `trading.trades.id`, but the `trades` table itself needs no new column beyond, at most, a nullable `external_reference VARCHAR` (an additive, backward-compatible migration, not a redesign) to record which broker-side trade a row corresponds to, if any.
- **TradingView Synchronization:** the same shape as Broker Integrations — an external reference and an upstream integration, not a change to Trading's own tables.
- **Mobile App:** consumes the exact same API (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8) as the web frontend — no schema implication at all. `identity`/`preferences` may eventually need a `device_tokens` table for push notifications (part of the reserved `notifications` schema, Section 3.2), not a change to any existing table.
- **Team Workspaces:** conditional on Product Bible Open Question 2. If it resolves toward yes, this is the multi-tenancy extension already anticipated: every table with a `user_id` gains a parallel `workspace_id` or `account_id` concept, and Row-Level Security policies (Section 11.2) are extended — a genuinely significant but purely additive change, not a rewrite of the tables' existing meaning.
- **Plugin System / Marketplace:** no corresponding entity in any frozen document. Registered as **Open Question DB-5** (Section 14) rather than speculatively designed.

---

## 13. Migration Strategy

### 13.1 Versioning Policy
Every schema change is a numbered, forward-only migration (the specific tool — e.g., Alembic, already used by the reference implementation — is an implementation decision per `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8, not fixed here). Each migration corresponds to exactly one entry in this document's own Document Control table (Section 16) once this document itself is revised — the same discipline `TRADEOS_DOMAIN_MODEL.md` Section 20 established for itself.

### 13.2 Backward Compatibility
A migration that only **adds** a nullable column, a new table, or a new lookup-table row (e.g., a new `engine_types` or `scoring_profiles` entry) is always backward compatible and may ship without coordinated application deployment. A migration that renames, narrows, or removes a column is a breaking change and must follow Section 13.3.

### 13.3 Breaking Changes
A breaking change (renaming/removing a column, tightening a constraint that existing data might violate) requires: (1) a migration that introduces the new shape *alongside* the old one, (2) an application deployment that writes to both and reads from the new one, (3) a data backfill confirming the new shape is fully populated for all existing rows, (4) only then, a final migration removing the old shape. This is standard expand/contract migration practice, named here because Section 1's Goal 1 (historical data must never silently change) makes skipping steps 1–3 a Correctness risk, not merely an inconvenience.

### 13.4 Data Migrations
Any migration that transforms existing data (not just schema shape) must be idempotent (safely re-runnable) and must never operate on the immutable tables (Section 9's first row) except to add wholly new rows — an immutable table's existing rows are never targets of a data migration's `UPDATE`.

---

## 14. Known Technical Debt / Open Questions

Per this document's own instruction: uncertain design decisions are registered here, not silently resolved.

| ID | Topic | Current State | Target State | Reason | Priority |
|---|---|---|---|---|---|
| DB-1 | "Calendar" module | Not modeled — no entity exists in any frozen document | Either a pure frontend view over existing `trades`/`journal_entries` (no schema change) or a genuinely new entity | The prompt for this document named "Calendar" as an example module, but no upstream document defines it | Low — resolve when/if the Domain Model is amended |
| DB-2 | Mistake tagging after Trade closure | Not blocked at the database level | Possibly restricted to an explicit, logged action once a Trade is `Closed` | Domain Model does not specify whether post-closure mistake tagging is a normal or a notable action | Low |
| DB-3 | "Risk Profiles" and "Application Configuration" | No corresponding entity in any frozen document | Either folded into `ScoringProfile` or modeled as a new Configuration concept | The prompt named these; the Domain Model does not yet | Medium — likely needed before real risk-rule enforcement (e.g., daily loss lock, mentioned in `TradeOS_PRODUCT.docx` v1.0) is built |
| DB-4 | Full point-in-time reconstruction of a Trade's past state | Only "that an amendment occurred" is logged (`platform.event_log`), not a full historical row | A `trades_history`-style table, if ever needed | Deferred deliberately to avoid full row-versioning overhead on every mutable table before it's shown necessary | Low |
| DB-5 | Plugin System / Marketplace | No corresponding entity anywhere | Unknown — needs product definition first | Named in the prompt, absent from the Product Bible's scope (`TRADEOS_PRODUCT_BIBLE.md` Section 11, Out of Scope) | Very low — not part of any current or near-term roadmap |

### 14.1 Resolved Decisions Log

Items previously registered as open and since confirmed by explicit decision — kept here as a record, not deleted, so the history of what was once uncertain is not lost (consistent with this document's own historical-integrity philosophy, Section 1).

| ID | Topic | Resolution | Confirmed |
|---|---|---|---|
| DB-6 (resolved) | Apparent Domain Model tension between Section 4.3 (Configuration owns the Mistake Tag catalog) and Section 4.6 (Mistake Tracking Context "owns the mistake taxonomy") | **Configuration owns the canonical mistake taxonomy** — categories, tag names, and descriptive metadata (`configuration.catalog_entries`, Section 6.8). **Mistake Tracking owns only analytical/statistical information derived from Trades** (frequency, cost, priority ranking) and stores none of it — a pure read-side service with no schema, the same shape as Analytics (Section 3.1). | 2026-07-24 |
| (resolved, no prior ID — Section 7.0) | Whether the five Evaluation Engines should be modeled as explicit columns or a fully generic per-engine table | **Explicit columns on `evaluation_snapshots`**, because the five engines are a stable business concept read together on nearly every access; **their configuration (criteria/weights/profiles/versions) remains fully data-driven.** A sixth engine is an additive migration (one new nullable column pair), never a generic redesign (Section 7.0). | 2026-07-24 |

---

## 15. Traceability Matrix

| Domain Model Entity | Database Table(s) | System Architecture Module | Future API Module (anticipated, not yet specified) |
|---|---|---|---|
| Trade | `trading.trades` | `trading` | Trades API |
| ChecklistSnapshot | `trading.checklist_snapshots` | `trading` | Trades API (nested resource) |
| EvaluationSnapshot | `trading.evaluation_snapshots` | `evaluation` (computes) / `trading` (stores) | Evaluation API |
| CriterionBreakdownRow | `trading.evaluation_snapshot_breakdowns` | `evaluation` (computes) / `trading` (stores) | Evaluation API (Rule Explorer endpoint) |
| ScoringCriterion | `configuration.scoring_criteria` | `configuration` | Configuration API |
| ScoringWeight | `configuration.scoring_weights` | `configuration` | Configuration API |
| ScoringConfiguration | `configuration.scoring_configuration_versions` | `configuration` | Configuration API |
| EngineType (enum) | `configuration.engine_types` | `configuration` | Configuration API |
| ScoringProfile (enum) | `configuration.scoring_profiles` | `configuration` | Configuration API |
| Catalog / CatalogEntry | `configuration.catalog_entries` | `configuration` | Catalogs API |
| PlaybookSetup | `playbook.playbook_setups`, `playbook.playbook_setup_attachments` | `playbook` | Playbook API |
| MistakeTag | `configuration.catalog_entries` (kind=mistake_tag) | `configuration` (catalog) / `mistake_tracking` (ranking, no schema) | Mistakes API |
| Trade↔Mistake relationship | `trading.trade_mistakes` | `trading` | Trades API (nested resource) |
| JournalEntry | `journal.journal_entries` | `journal` | Journal API |
| UserAccount | `identity.user_accounts` | `identity` | Auth API |
| UserPreferences | `preferences.user_preferences` | `preferences` | Settings API |
| (Domain Events, all) | `platform.event_log` | `platform` (cross-cutting) | Not directly exposed; internal observability |

Every row in Section 6 appears here. Any future table must appear as a new row in this matrix before being implemented — this is what "traceable back to the Domain Model" means in practice, matching `TRADEOS_DOMAIN_MODEL.md` Section 18's own standard.

---

## 16. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial canonical Database Design. Derived from `TRADEOS_PRODUCT_BIBLE.md` v2.1, `TRADEOS_DOMAIN_MODEL.md` v1.1, and `TRADEOS_SYSTEM_ARCHITECTURE.md` v1.1. Defined schema organization (one Postgres schema per Bounded Context), naming/UUID/timestamp/soft-delete/audit strategy, full entity-to-table mapping, all relationships, complete table specifications, the Evaluation Engine's config-driven storage design, historical data strategy, performance/security/scalability/migration strategy, and a full traceability matrix. Registered six open questions (DB-1 through DB-6) rather than inventing answers. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Confirmed (Section 7.0) that the five Evaluation Engines are modeled as explicit, stable columns on `evaluation_snapshots` while their configuration remains fully data-driven, with a sixth engine handled as an additive migration, never a generic redesign. Confirmed (Section 3.1, 6.8) that Configuration owns the canonical mistake taxonomy (categories, tags, metadata) while Mistake Tracking owns only analytical/statistical information derived from Trades, with no schema of its own. Resolved DB-6 and moved it to a new Resolved Decisions Log (Section 14.1) rather than deleting the record of it having once been open. |
| 1.2 | 2026-07-30 | Downstream of `TRADEOS_DOMAIN_MODEL.md` v2.0 (KDD-07, a MAJOR change there). `trading.trades` (Section 6.9): added `status` (`planned`\|`open`\|`closed`), `take_profit`, `margin_used`; relaxed `entry_price`/`stop_loss`/`entered_at` from `NOT NULL` (absent while `status='planned'`); redefined `result` (`NOT NULL DEFAULT 'open'` → `NULL`, values narrowed to `tp`\|`sl`\|`be`, `'open'` retired); redefined the CHECK constraints realizing INV-TRADE-01/02 accordingly; `entered_at`'s index becomes partial (`WHERE entered_at IS NOT NULL`). Explicitly did **not** add `roi_percent`/`pnl_percent` columns — both remain computed-only (Domain Model DI-14). |

**Status:** FROZEN. This is the fourth permanent foundational document of TradeOS, after `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, and `TRADEOS_SYSTEM_ARCHITECTURE.md`.
**Next document:** to be determined — likely an API specification, per the traceability matrix's "Future API Module" column.
