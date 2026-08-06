# TRADEOS_API_SPECIFICATION.md

**Document Status:** CANONICAL AND FROZEN — the official API specification of TradeOS.
**Version:** 1.3
**Last Updated:** 2026-08-05
**Depends On:** all five prior frozen documents (`PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, `TRADEOS_DATABASE_DESIGN.md`). This document invents no business rule, entity, or table — it defines the contract through which the business capabilities already modeled become callable.
**Is Not:** implementation code, controllers, DTOs, services, or an OpenAPI/Swagger document. It contains enough structure to generate one later (Section 16) without being one.

---

## 1. API Philosophy

1. **Business-first, not table-first.** An endpoint exists because a Domain Model capability (`TRADEOS_DOMAIN_MODEL.md` Sections 8, 12) needs to be callable — never because a database table (`TRADEOS_DATABASE_DESIGN.md`) exists and "should have CRUD." This is why, for example, there is no `DELETE /scoring-criteria/{id}` (deactivation is a business action with its own meaning, Domain Invariant DI-10) and no generic `PATCH /trades/{id}/evaluation-snapshot` (a snapshot is never edited, Domain Invariant DI-06 — it is only produced by registering or re-evaluating a Trade).
2. **Resource-oriented.** URLs name things (`/trades`, `/playbook-setups`), not actions (never `/getTrade` or `/calculateScore`). Actions that don't fit a resource's default CRUD shape are modeled as sub-resources or explicit action endpoints (Section 3.5), not verbs bolted onto a noun.
3. **Consistent naming.** Plural, kebab-case resource paths; `snake_case` in JSON bodies (matching the database's own convention, `TRADEOS_DATABASE_DESIGN.md` Section 2.3) so no silent translation layer exists between what the database calls a field and what the API calls it.
4. **Predictable behavior.** The same filtering, pagination, and error shape (Sections 7–8) apply everywhere. A developer who has learned one endpoint has learned the shape of all of them.
5. **Stateless.** No endpoint depends on server-side session state between requests (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9.1) — every request carries everything needed to authenticate and authorize it (Section 4).
6. **Versioned from day one.** Even with one client and one user today, the URL carries a version segment (Section 3.2) so that breaking changes have a home that isn't "renegotiate the whole API."
7. **Secure by default.** Every endpoint requires authentication unless explicitly documented otherwise (Section 4); there is no "internal, so it's fine unauthenticated" endpoint.
8. **The API is stable even if storage changes.** Nothing in this document names a database schema, table, or column directly — every request/response field is named after a Domain Model or Value Object concept (`TRADEOS_DOMAIN_MODEL.md` Section 2, Ubiquitous Language), so `TRADEOS_DATABASE_DESIGN.md` could evolve its internal storage shape (Section 13 there) without this contract needing to change.

---

## 2. API Design Principles

Where Section 1 explains the *stance* this API takes, this section is the concrete, tactical checklist every new or changed endpoint must satisfy before it ships. It is to Section 1 what `TRADEOS_SYSTEM_ARCHITECTURE.md`'s Architectural Principles are to the Product Bible's Product Principles: narrower, more mechanical, and directly enforceable in review.

1. **Traceable before built.** No endpoint is added without first appearing as a row in the Traceability Matrix (Section 19) — if a proposed endpoint has no business capability, Domain Model entity, and database module to point to, it is not ready to be designed, let alone built.
2. **One error shape, no exceptions.** Every endpoint, without exception, returns the envelope defined in Section 8 on failure. An endpoint that invents its own error shape is a defect, not a stylistic choice.
3. **One pagination mechanism, no exceptions.** Every list endpoint uses the cursor-based contract in Section 7.4, including catalogs and other small collections — consistency is preferred over a "big collections get cursors, small ones get offsets" special case.
4. **Every invariant violation names its invariant.** A write endpoint that rejects a request because of a Domain Invariant (`TRADEOS_DOMAIN_MODEL.md` Section 15) must return that invariant's ID in the error's `details` (Section 8) — never a generic message a developer has to reverse-engineer.
5. **Authorization is one rule, applied uniformly.** Every endpoint resolves authorization through the single ownership rule in Section 4.6 — no endpoint implements its own bespoke permission check.
6. **Speak the Domain Model's language, not the database's.** Request and response field names come from `TRADEOS_DOMAIN_MODEL.md` Section 2 (Ubiquitous Language), never a raw column name lifted from `TRADEOS_DATABASE_DESIGN.md` — this is what keeps the API stable while storage evolves (Section 1, Principle 8).
7. **A named business action gets a named endpoint.** Anything that is not "read a resource" or "change a field" — closing a trade, publishing a configuration version, deactivating a catalog entry — is modeled as its own `POST` sub-path (Section 3.5), never smuggled into a generic `PATCH`.
8. **Additive by default; breaking changes get a new version.** An endpoint's shape only ever grows in a backward-compatible way within its version (Section 12); anything that would change existing behavior for existing callers is a new version, never an in-place edit.

---

## 3. API Architecture

### 3.1 Style
REST over HTTPS, JSON request/response bodies. Confirmed, not reopened, from `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 8 (no GraphQL/gRPC until a concrete need — e.g., a future mobile client requiring field-level selection — arises).

### 3.2 Versioning Strategy
URL path versioning: `/api/v1/...`. All endpoints in this document are `v1`. A breaking change (Section 12) is introduced as `/api/v2/...` for the affected resource only — this API does not version the entire surface at once, only the resources that actually changed, to avoid forcing frontend upgrades for unrelated modules.

**One deliberate exception:** the health-check endpoint (Section 6.0) lives outside `/api/v1` entirely. It is infrastructure (a process-liveness signal for hosting-platform probes), not a versioned business resource — versioning it alongside `Trades`/`Configuration`/etc. would incorrectly imply it is subject to the same deprecation lifecycle (Section 13) as business capabilities.

### 3.3 URL Conventions
- Collection: `/api/v1/trades` (plural noun).
- Single resource: `/api/v1/trades/{id}`.
- Sub-resource / owned collection: `/api/v1/trades/{id}/mistakes`.
- Action that doesn't fit CRUD (Section 3.5): `/api/v1/trades/{id}/close`, `/api/v1/configuration/versions/{id}/publish`.
- Query parameters for filtering/sorting/pagination only (Section 7) — never for identifying a specific resource (that is always a path parameter).

### 3.4 HTTP Methods

| Method | Meaning | Idempotent? |
|---|---|---|
| `GET` | Read a resource or collection | Yes |
| `POST` | Create a resource, **or** perform a named business action that doesn't map to a CRUD verb (Section 3.5) | No, unless an `Idempotency-Key` header is supplied (Section 3.6) |
| `PATCH` | Partially update a resource's mutable fields | Yes (applying the same patch twice yields the same state) |
| `DELETE` | Soft-delete (never hard-delete, `TRADEOS_DATABASE_DESIGN.md` Section 2.6) | Yes |

**`PUT` is deliberately not used anywhere in this API.** Every resource's mutable shape is small enough that `PATCH` fully covers partial updates, and no resource is ever wholesale-replaced (replacing a `Trade` wholesale would bypass its invariants, Section 9).

### 3.5 Business Actions That Are Not Plain CRUD

Several Domain Model operations are not "update a field" — they are meaningful business events with their own validation and side effects (`TRADEOS_DOMAIN_MODEL.md` Section 11). These are modeled as `POST` to a sub-path naming the action, never as a `PATCH` that happens to change a status field:

- `POST /trades/{id}/close` — not `PATCH /trades/{id}` with `result` in the body — because closing enforces Domain Invariant INV-TRADE-02 (Result and Exit Price must arrive together) and triggers a distinct Domain Event (`TradeClosed`) with its own downstream consequences (Section 11).
- `POST /trades/{id}/reevaluate` — an explicit, separate action, never a side effect of anything else (`TRADEOS_DOMAIN_MODEL.md` Section 8.2: re-evaluation is "never automatic").
- `POST /configuration/versions/{id}/publish` — publishing a configuration version is irreversible in effect (the prior version becomes `superseded`, `TRADEOS_DATABASE_DESIGN.md` Section 6.6) and deserves its own audited action, not a `status` field `PATCH`.
- `POST /configuration/scoring-criteria/{id}/deactivate`, `POST /catalogs/{id}/deactivate` — deactivation is a one-way, meaningful business action (Domain Invariant DI-10), not a boolean flag flip indistinguishable from any other edit.

### 3.6 Idempotency

Every `POST` that creates a resource (never a `POST` that performs an action like `close` or `publish`) accepts an optional `Idempotency-Key` header. If a request with a previously-seen key arrives again, the API returns the original response without creating a duplicate resource. This matters most for `POST /trades` — a network retry after a timeout must never risk double-logging a trade.

### 3.7 Error Handling Philosophy
One consistent error envelope (Section 8) for every failure mode, everywhere. A client never needs to guess whether a 400 means a validation failure or a business-rule violation — the envelope's `code` always disambiguates.

---

## 4. Authentication & Authorization

### 4.1 Authentication Flow
Token-based, per `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-07: a client exchanges credentials for a short-lived **access token** (JWT) and a longer-lived **refresh token**. The access token is sent as `Authorization: Bearer <token>` on every subsequent request. When it expires, the refresh token is exchanged for a new pair without re-entering credentials.

### 4.2 JWT
The access token's claims include, at minimum, the authenticated `user_id` (`TRADEOS_DOMAIN_MODEL.md` Section 8.11, `UserAccount`) and its own expiry. It carries no business data (no cached Trade or Evaluation data) — it exists only to answer "who is calling," never "what may they see," which is resolved fresh on every request (Section 4.4).

### 4.3 Refresh Tokens
Issued alongside the access token at login, stored by the client, and single-use: exchanging a refresh token invalidates it and issues a new one (rotation), so a leaked, already-used refresh token is not silently replayable. Refresh tokens are revocable server-side (supporting `POST /auth/logout`, Section 6).

### 4.4 Session Handling
No server-side session state (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9.1) — every request is independently authenticated via its bearer token. "Logging out" means revoking the refresh token; it does not invalidate an already-issued access token before its natural expiry (a deliberate, standard tradeoff of short-lived access tokens over server-side session invalidation, keeping the system stateless).

### 4.5 Permissions and Roles
**Today, there is exactly one role: the authenticated owner of their own data** (`TRADEOS_PRODUCT_BIBLE.md` Section 4.2). There is no admin role, no read-only role, and no shared/team access — building any of this now would be speculative against Product Bible Open Question 2 and would violate `TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 4. Every endpoint's authorization check is therefore reducible to one rule (Section 4.6).

### 4.6 Ownership Rules
**The single authorization rule for this entire API:** a request may only read or write a resource that is transitively owned by the requesting `user_id` (`TRADEOS_DATABASE_DESIGN.md` Section 11.2's row-ownership columns). For `Trade`, `JournalEntry`: direct ownership via `user_id`. For `ChecklistSnapshot`, `EvaluationSnapshot`, `evaluation_snapshot_breakdowns`, tagged Mistakes: transitive ownership via the parent `Trade`. `Configuration` resources (criteria, weights, versions, catalogs) and `PlaybookSetup` are, today, global to the single user — not yet modeled as owned by anyone specifically, because multi-user configuration ownership is conditional on Open Question 2 (Section 4.7).

### 4.7 Future Multi-User Support (Explicitly Conditional)
If Product Bible Open Question 2 resolves toward multi-user, this section — not the rest of the API — is what changes: real roles (e.g., a workspace admin who can edit shared Configuration versus a member who cannot), and `Configuration`/`Catalog`/`PlaybookSetup` resources gaining their own ownership scope. Because every endpoint below already resolves authorization through a single, centrally-checked rule (Section 4.6) rather than ad hoc per-endpoint logic, this is an extension of that rule, not a redesign of every endpoint — matching `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 10.2's promised migration path.

---

## 5. API Modules

Grouped by Bounded Context (`TRADEOS_DOMAIN_MODEL.md` Section 4), matching `TRADEOS_DATABASE_DESIGN.md` Section 3's schema boundaries exactly — the same module boundary is enforced in code, storage, and now the API, for the same reason each time (`TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 2).

| Module | Responsibility | Confirmed? |
|---|---|---|
| **Authentication** | Credential exchange, token issuance/refresh/revocation | Yes |
| **Users** | The authenticated user's own identity record | Yes (minimal, Generic Domain) |
| **Preferences** | Theme, language, notification settings | Yes (Generic Domain) |
| **Trades** | Registering, amending, closing, and querying Trades; their Checklist/Evaluation Snapshots; their tagged Mistakes | Yes — the busiest module |
| **Evaluation** | Computing scores (live preview) and explaining historical scores (Rule Explorer) | Yes — Core Domain |
| **Configuration** | Scoring criteria, weights, versions, profiles, engine types | Yes |
| **Catalogs** | Setups, Sessions, Strategies, Entry Triggers, Mistake Tags | Yes |
| **Playbook** | Setup definitions and attachments | Yes |
| **Mistakes** | Read-only frequency/cost/priority ranking | Yes (no writes — mistakes are tagged via the Trades module) |
| **Statistics** | Read-only performance analytics, all-time and rolling | Yes |
| **Journal** | Free-text reflection | Yes |
| **Dashboard** | A single composition endpoint for the frontend home view | Yes, but **not a Bounded Context** — see Section 5.1 |
| **Health Check** | A liveness signal for hosting-platform infrastructure (load balancers, orchestrators) | Yes, but **not a Bounded Context, and not a business module at all** — see Section 5.2 |
| **Trading Accounts, Reports, AI, Notifications, Calendar** | Named in the prompt for this document | **Not confirmed** — see Section 17 |

### 5.1 Dashboard Is a Composition, Not a New Bounded Context
`GET /api/v1/dashboard` exists purely for frontend convenience — it composes calls already available individually through Statistics and Trades into one response, sparing the frontend N round-trips for a single screen. It introduces no new business capability and owns no data. This is stated explicitly so it is never mistaken for evidence that "Dashboard" deserves its own Bounded Context — it does not (Domain Model Section 4 names no such context, and none is needed).

### 5.2 Health Check Is Cross-Cutting Infrastructure, Not a Bounded Context
`GET /healthz` (Section 6.0) exists to resolve `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Open Question OQ-1 and `TRADEOS_BACKEND_BLUEPRINT.md` Known Gap BE-7 — Phase 9 (Deployment & Production Hardening)'s Sprint 9.1 cannot be exit-verified without a defined contract a hosting platform's readiness probe can call. It has no Domain Model entity, owns no data, requires no authentication, and is not versioned under `/api/v1` (Section 3.2). It is listed in the module table above only for discoverability, not because it is a Bounded Context or even a business capability.

---

## 6. Endpoint Specifications

**Scoping note:** per this document's mandate to be complete without becoming unusable, every endpoint is listed with its full contract (URL, method, auth, request, response, status codes). The eight endpoints most illustrative of a pattern used repeatedly elsewhere (trade registration, trade closure, re-evaluation, evaluation preview, configuration publishing, catalog deactivation, statistics by-dimension, journal creation) are specified in full prose detail. The remainder follow the identical shape and are specified in compact table form — omitting a field from a compact entry means it follows the same rule already established by the nearest full-detail sibling endpoint (e.g., all `GET` list endpoints share one pagination contract, Section 7).

### 6.0 Health Check (Cross-Cutting — No Bounded Context, Section 5.2)

#### `GET /healthz`
- **Purpose:** a liveness signal — confirms the backend process is running and able to handle requests. Resolves `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Open Question OQ-1 and `TRADEOS_BACKEND_BLUEPRINT.md` Known Gap BE-7.
- **Path:** deliberately outside `/api/v1` (Section 3.2) — this is infrastructure, not a versioned business resource.
- **Auth Required:** No. Exempt from `AuthenticationMiddleware` entirely (added to the same `PUBLIC_PATHS` mechanism already used for `/api/v1/auth/register`, `/login`, `/refresh`) — a load balancer or orchestrator's probe cannot authenticate.
- **Scope — liveness only, not readiness:** this endpoint does **not** check database connectivity or any other dependency. A transient database hiccup should not cause a hosting platform to kill and restart an otherwise-healthy backend process — that would trade a recoverable, transient condition for an unnecessary restart, disproportionate to this project's current scale (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.4). If a real readiness probe (one that does check dependencies) becomes necessary because of a specific hosting platform's requirements or a genuine future operational need, it must be introduced as a **separate, new endpoint** (e.g., `GET /readyz`) — never by expanding this endpoint's contract to silently start checking dependencies callers did not ask it to check.
- **Request Body:** none.
- **Response Body (200):** `{ "status": "ok" }`.
- **Status Codes:** `200` only. If the process cannot respond at all, the absence of a response (connection refused/timeout) *is* the failure signal — there is no defined non-200 response body for this endpoint to return, since a process able to construct and return JSON is, by this endpoint's own definition, live.
- **Contract stability — intentionally minimal, deliberately extensible:** the response body above is the complete v1 contract. Callers **must** treat any field beyond `status` as absent — do not assume today's shape (`{"status": "ok"}` and nothing else) is exhaustive going forward. Additional, purely informational fields (e.g., `version`, `commit`, `uptime`) may be added in a future revision of this document **without** that being a breaking change and without a `v2` — the only guarantee this contract makes, now and after any such addition, is that a live process returns HTTP `200` with a JSON body whose `status` field equals the string `"ok"`. A client (or an operator's monitoring script) that keys its liveness check on anything other than `status == "ok"` is depending on behavior this contract does not promise.

### 6.1 Authentication Module

#### `POST /api/v1/auth/register`
- **Purpose:** create a new `UserAccount` (Domain Model Section 8.11).
- **Auth Required:** No.
- **Request Body:** `email` (string, required, valid email format), `password` (string, required, minimum length per Section 9 validation rules).
- **Response Body (201):** `{ "user_id": "<uuid>", "email": "<string>" }`. Does not return an access token — the client must still log in (kept as two distinct steps deliberately, so "an account exists" and "this device is authenticated" are never conflated).
- **Status Codes:** `201` Created; `409` Conflict (email already registered); `422` Validation Error.
- **Business Validation:** email uniqueness (`TRADEOS_DATABASE_DESIGN.md` Section 6.1's `UNIQUE` constraint, surfaced here as a `409`, not a generic `422`, since it is a conflict with existing data, not a malformed request).

#### `POST /api/v1/auth/login`
- **Purpose:** exchange credentials for an access/refresh token pair.
- **Auth Required:** No.
- **Request Body:** `email`, `password`.
- **Response Body (200):** `{ "access_token": "<jwt>", "refresh_token": "<string>", "expires_in": <seconds> }`.
- **Status Codes:** `200`; `401` Unauthorized (invalid credentials — deliberately identical error whether the email doesn't exist or the password is wrong, to avoid confirming which emails are registered).

#### `POST /api/v1/auth/refresh`
- **Purpose:** exchange a valid refresh token for a new access/refresh pair (Section 4.3, rotation).
- **Auth Required:** No (the refresh token itself is the credential).
- **Request Body:** `refresh_token`.
- **Response Body (200):** same shape as login.
- **Status Codes:** `200`; `401` (refresh token invalid, expired, or already used).

#### `POST /api/v1/auth/logout`
- **Purpose:** revoke the current refresh token (Section 4.4).
- **Auth Required:** Yes.
- **Request Body:** none.
- **Response:** `204` No Content.

### 6.2 Users Module

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `/api/v1/users/me` | GET | Return the authenticated user's own account record | Yes | Never accepts a `{userId}` path parameter — "me" is always resolved from the token (Section 4.6), preventing any accidental cross-user lookup at the URL level |
| `/api/v1/users/me` | PATCH | Update email (password change is a distinct, dedicated endpoint, not shown here as out of scope for v1's minimal Generic Domain treatment, Domain Model Section 3.4) | Yes | `409` if the new email is already taken |

### 6.3 Preferences Module

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `/api/v1/preferences` | GET | Return the current user's preferences (`TRADEOS_DOMAIN_MODEL.md` Section 8.12) | Yes | Created automatically with defaults at registration — this endpoint never 404s for an authenticated user |
| `/api/v1/preferences` | PATCH | Update theme/language/notification settings | Yes | No business validation beyond allowed enum values for `theme`/`language` |

### 6.4 Trades Module *(v2.0 fields — see `TRADEOS_DOMAIN_MODEL.md` KDD-07)*

#### `POST /api/v1/trades`
- **Purpose:** register a new Trade — the single most important write in the system. Triggers synchronous Evaluation (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4; Section 11.1 of this document traces the full flow) **only when `status != planned`** — a `Planned` Trade has no Checklist/Evaluation yet by definition (Domain Invariant DI-13).
- **Auth Required:** Yes. **Permissions:** none beyond ownership (Section 4.6) — the created Trade is owned by the caller.
- **Headers:** optional `Idempotency-Key` (Section 3.6).
- **Request Body:**
  - Core facts (always required): `market`, `direction` (`long`|`short`), `status` (`planned`|`open`|`closed`, **new in v2.0** — no default, always explicit).
  - `scoring_profile` (required unless `status = planned` — a `Planned` Trade has no Evaluation to configure yet; required exactly as before, Sprint 4.1's resolution, once `status != planned`).
  - Required when `status = open` or `status = closed`: `entry_price`, `stop_loss`, `entered_at` (**relaxed from always-required in v2.0** — absent entirely while `status = planned`).
  - Required additionally when `status = closed`: `exit_price`, `result` (`tp`|`sl`|`be`), `closed_at`, `realized_pnl` (**new in v2.0**, INV-TRADE-02 — a trader-supplied fact, never derived, Domain Model Section 8.1's Owned Information).
  - Optional at any status: `take_profit` (**new in v2.0**), `margin_used` (**new in v2.0** — distinct from `size`), `size`, `leverage`, `strategy_id`, `setup_id`, `session_id`, `entry_trigger_id`, `notes`, `mfe_price`, `mae_price`.
  - `checklist_answers` (object, optional, ignored while `status = planned`): the raw `{criterion_source_field: value}` map (`TRADEOS_DATABASE_DESIGN.md` Section 6.10) feeding Confidence/Market Context/Bias. Omitted fields simply mean those criteria don't contribute to this Trade's score (Domain Invariant INV-WEIGHT-01 handles a missing input the same way it handles a deactivated criterion).
  - `mistake_ids` (array of catalog entry IDs, optional): tag Mistakes at creation time, equivalent to calling Section 6.4's mistake-tagging endpoint immediately after.
- **Response Body (201):** the full Trade representation, including its computed properties (`r_multiple`, `mfe_r`, `mae_r`, `captured_pct`, `potential_left_r`, `roi_percent`, `pnl_percent` — **the last two new in v2.0**, computed at response time from `realized_pnl`/`margin_used`/`leverage`, never stored, `TRADEOS_DATABASE_DESIGN.md` Section 6.9) and its nested current `evaluation` object (`null` while `status = planned`; scores + grades for all active engines otherwise, Section 6.5).
- **Status Codes:** `201` Created; `422` Validation Error (Domain Invariant INV-TRADE-01, e.g., stop on the wrong side of entry, or a field required for the given `status` is missing); `401` Unauthorized.
- **Business Validation Rules:** INV-TRADE-01 (stop placement relative to direction, checked only once both prices exist); INV-TRADE-02 (redefined, v2.0 — see Domain Model Section 15) enforces exactly which fields exist per `status`.
- **Notes:** this endpoint performs the entire flow described in Section 11.1 within one request/response cycle and one database transaction — the client receives the final, scored Trade in the same response, never a "submitted, check back later" acknowledgment (this is not a Long Running Operation, Section 10). This is unchanged for `status != planned`; a `Planned` Trade simply skips the Evaluation portion of that flow.

#### `GET /api/v1/trades`
- **Purpose:** list the caller's Trades.
- **Query Parameters:** filtering, sorting, pagination per Section 7 (e.g., `?direction=long&status=closed&result=tp&entered_after=2026-01-01&sort=-entered_at&limit=50&cursor=...`). `?status=planned|open|closed` is a filter **new in v2.0**; `result` no longer accepts `open` as a value (retired, see `TRADEOS_DOMAIN_MODEL.md` KDD-07) — filtering for not-yet-closed Trades is now `?status=open` (or `?status=planned`), not `?result=open`.
- **Response Body (200):** paginated envelope (Section 7.4) of Trade summaries (a lighter shape than the full detail view — omits `evaluation_snapshot_breakdowns` and `checklist_answers`, which are fetched only via the single-resource endpoint, to keep list responses cheap).

#### `GET /api/v1/trades/{id}`
- **Purpose:** full detail of one Trade, including its current Evaluation Snapshot (Section 6.5) but not its full historical breakdown (that is `GET /trades/{id}/evaluation`, kept separate because it's a heavier payload not needed every time a Trade is viewed).
- **Status Codes:** `200`; `404` (not found, or not owned by the caller — identical response for both, so ownership is never leaked by a different error shape, Section 14).

#### `PATCH /api/v1/trades/{id}`
- **Purpose:** amend already-recorded facts (e.g., correct a mistyped entry price).
- **Business Validation:** re-validates INV-TRADE-01/02 against the *proposed* full state, not just the changed field, since a partial patch could otherwise create an inconsistent combination (e.g., changing `direction` without changing `stop_loss`).
- **Side Effect (documented, not hidden):** raises a `TradeAmended` Domain Event (Section 11) — the amendment is never silent (Domain Invariant DI-01).
- **Notes:** does **not** re-run Evaluation. If the amendment should affect scoring, the caller must separately call `POST /trades/{id}/reevaluate` (Section 6.4) — kept as two explicit steps because Domain Model Section 8.2 requires re-evaluation to always be a deliberate action, never an automatic side effect of an unrelated edit.

#### `POST /api/v1/trades/{id}/open` *(new in v2.0)*
- **Purpose:** transition a Trade from `Planned` to `Open` — the first moment it becomes a real, executed position. Triggers Evaluation for the first time (same synchronous flow `POST /trades` already performs when created directly as `Open`, Section 11.1).
- **Request Body:** `entry_price` (required), `entered_at` (required), `scoring_profile` (required — Evaluation runs here), `stop_loss`/`take_profit`/`checklist_answers` (optional, same shape as `POST /trades`).
- **Response Body (200):** the updated Trade, `status = open`, with its nested current `evaluation` object now present.
- **Status Codes:** `200`; `409` Conflict (Trade is not `Planned` — mirrors `close`'s own "not idempotent" posture, Domain Invariant DI-13/INV-TRADE-04); `422` (missing required field, or INV-TRADE-01 violated).
- **Event:** raises `TradeOpened` (Section 11).

#### `POST /api/v1/trades/{id}/close`
- **Purpose:** transition a Trade from `Open` to `Closed`, with a terminal `Result`.
- **Request Body:** `result` (`tp`|`sl`|`be`, required), `exit_price` (required — INV-TRADE-02), `realized_pnl` (required, **new in v2.0** — a trader-supplied fact, e.g. from the exchange, never derived from price/size alone since fees/funding are not captured), `closed_at` (required), `mfe_price`/`mae_price` (optional, but this is the natural moment to supply them since the trade's full excursion is now known).
- **Response Body (200):** the updated Trade, with its now-computable `r_multiple`/`mfe_r`/`mae_r`/`captured_pct`/`potential_left_r`/`roi_percent`/`pnl_percent`.
- **Status Codes:** `200`; `409` Conflict (not `Open` — a `Planned` Trade must call `open` first, INV-TRADE-04; an already-`Closed` Trade rejects outright, closing is not idempotent in the sense of "closing twice with different prices silently wins"); `422` (missing a required field).
- **Event:** raises `TradeClosed` (Section 11).

#### `POST /api/v1/trades/{id}/reevaluate`
- **Purpose:** the explicit, deliberate re-scoring action (`TRADEOS_DOMAIN_MODEL.md` Section 8.2).
- **Request Body:** `configuration_version_id` (optional — defaults to the currently-published version if omitted).
- **Response Body (200):** the new Evaluation Snapshot. The previous snapshot is **not** deleted (`TRADEOS_DATABASE_DESIGN.md` Section 6.12 — `is_current` flips, old row persists), and remains visible via `GET /trades/{id}/evaluation` (Section 6.5, history view).
- **Status Codes:** `200`; `404` (Trade or specified configuration version not found).
- **Business Validation:** the specified `configuration_version_id` must have `status = published` — re-evaluating against a `draft` version is rejected (`422`), since a draft is, by definition, not yet a trustworthy, stable configuration to score against.

#### `DELETE /api/v1/trades/{id}`
- **Purpose:** soft-delete (Section 3.4) — marks `deleted_at`, per `TRADEOS_DATABASE_DESIGN.md` Section 2.6, for a genuine data-entry mistake (e.g., an accidental duplicate).
- **Status Codes:** `204`; `404`.
- **Notes:** does not delete the Trade's Checklist/Evaluation Snapshots or Journal references — they remain in storage, orphaned but intact, exactly as `TRADEOS_DATABASE_DESIGN.md` Section 2.6 specifies. This endpoint is **not** for closing a trade (use `close`) and is expected to be rare.

#### Mistakes on a Trade

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/trades/{id}/mistakes` | GET | List Mistake Tags currently attached to this Trade |
| `/api/v1/trades/{id}/mistakes` | POST | Attach a Mistake Tag (`{ "catalog_entry_id": "<uuid>" }`); raises `MistakeTagged` (Section 11) |
| `/api/v1/trades/{id}/mistakes/{catalogEntryId}` | DELETE | Remove a tag |

### 6.5 Evaluation Module

#### `POST /api/v1/evaluation/preview`
- **Purpose:** compute Confidence/Quality/Execution/Market Context/Bias scores from a supplied set of checklist-style answers **without creating or modifying any Trade** — the mechanism behind a live-updating score preview in the Checklist UI (`TRADEOS_PRODUCT_BIBLE.md` Section 9, Checklist module).
- **Auth Required:** Yes (still an authenticated operation, even though it persists nothing, to prevent this from being an open computation-as-a-service endpoint for non-users).
- **Request Body:** `checklist_answers` (the same shape as `POST /trades`), `scoring_profile` (required — Confidence/Bias/Market Context weights vary by profile, `TRADEOS_DOMAIN_MODEL.md` Section 8.6), `configuration_version_id` (optional, defaults to currently published).
- **Response Body (200):** the same Evaluation result shape as an `EvaluationSnapshot` (scores, grades, full per-criterion breakdown) — but **this response is never persisted anywhere**, and carries no `id`, since it is not an entity, only a computed value (Domain Model Section 12.1: "a pure function... holds no state").
- **Status Codes:** `200`; `422` (unrecognized `scoring_profile` or malformed `checklist_answers`).

#### `GET /api/v1/trades/{id}/evaluation`
- **Purpose:** the current Evaluation Snapshot for a Trade, with full criterion-level breakdown (the "Rule Explorer," `TRADEOS_PRODUCT_BIBLE.md` Principle 10).
- **Response Body (200):** `{ "confidence": { "score": ..., "grade": ..., "breakdown": [...] }, "quality": {...}, "execution": {...}, "market_context": {...}, "bias": { "score": ..., "breakdown": [...] } }` — no `grade` key under `bias`, consistent with `TRADEOS_DATABASE_DESIGN.md` Section 6.12's note that a signed engine has no letter grade.

#### `GET /api/v1/trades/{id}/evaluation/history`
- **Purpose:** every Evaluation Snapshot ever produced for this Trade (current and superseded), each tagged with which `configuration_version_id` produced it — the endpoint that makes Domain Invariant DI-06/DI-07's reproducibility guarantee actually inspectable.
- **Response Body (200):** an array, ordered newest first, each entry shaped like Section 6.5's single-snapshot response plus `is_current` and `created_at`.

### 6.6 Configuration Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/configuration/engine-types` | GET | List the (currently five) Evaluation Engines | Read-heavy, changes rarely |
| `/api/v1/configuration/scoring-profiles` | GET | List scoring profiles | |
| `/api/v1/configuration/scoring-profiles` | POST | Add a new profile (Section 7.0 of the Database Design — adding a profile is a data change) | |
| `/api/v1/configuration/scoring-criteria` | GET | List criteria, filterable by `engine_type` | |
| `/api/v1/configuration/scoring-criteria` | POST | Define a new criterion | Validates `max_value >= min_value` |
| `/api/v1/configuration/scoring-criteria/{id}` | PATCH | Edit a criterion's definition (name, description, range, category map) | Does **not** allow changing `engine_type_code` after creation — that would silently reinterpret every historical breakdown row referencing it; changing which engine a criterion belongs to requires deactivating the old one and creating a new one |
| `/api/v1/configuration/scoring-criteria/{id}/deactivate` | POST | Deactivate (Section 3.5) | Never a hard delete |

#### `GET /api/v1/configuration/versions`
- **Purpose:** list all Scoring Configuration Versions, with `status`.

#### `POST /api/v1/configuration/versions`
- **Purpose:** create a new **draft** version (copying forward the currently-published version's weights as a starting point, per typical editing workflow — though this is an implementation convenience, not a business rule this document mandates).
- **Response Body (201):** the new version, `status = draft`.

#### `POST /api/v1/configuration/versions/{id}/weights`
- **Purpose:** add or update a `ScoringWeight` row within a **draft** version only.
- **Request Body:** `criterion_id`, `profile_code`, `weight`, `is_active`.
- **Status Codes:** `409` if the target version's `status != draft` — **published versions are immutable** (`TRADEOS_DATABASE_DESIGN.md` Section 6.6), and this is the endpoint-level enforcement of that.

#### `POST /api/v1/configuration/versions/{id}/publish`
- **Purpose:** the single most consequential Configuration action — makes a draft version the live one.
- **Request Body:** none.
- **Response Body (200):** the version, now `status = published`, `published_at` set.
- **Side Effects:** the previously-published version transitions to `superseded` (never deleted); raises `ScoringConfigurationChanged` (Section 11). **Does not** trigger re-evaluation of any existing Trade — that remains a separate, explicit action per Trade (`POST /trades/{id}/reevaluate`, Section 6.4), exactly per Domain Model Section 8.2.
- **Business Validation:** every `ScoringCriterion` referenced by an active `ScoringWeight` in this version must itself be active (rejecting a version that would silently score against a deactivated criterion) — `422` if violated.
- **Status Codes:** `200`; `409` (version already published or superseded); `422` (internal inconsistency check failed).

### 6.7 Catalogs Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/catalogs` | GET | List catalog entries, filterable by `?kind=setup\|session\|strategy\|entry_trigger\|mistake_tag` | `kind` filter is effectively required for any usable response — an unfiltered call returns all kinds together, mainly useful for an admin/config screen, not day-to-day use |
| `/api/v1/catalogs` | POST | Create a new entry | `409` if `(kind, name)` already exists (`TRADEOS_DATABASE_DESIGN.md` Section 6.8's unique constraint) |
| `/api/v1/catalogs/{id}` | PATCH | Rename or edit metadata | Renaming does not affect historical Trades referencing this entry by ID (Domain Invariant DI-09) |
| `/api/v1/catalogs/{id}/deactivate` | POST | Deactivate | Never a hard delete (Domain Invariant DI-10); a Trade already referencing this entry is entirely unaffected |

### 6.8 Playbook Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/playbook-setups` | GET | List setups | |
| `/api/v1/playbook-setups` | POST | Create a setup definition, linked to an existing `catalog_entries` (kind=setup) row | `422` if the referenced catalog entry is not `kind=setup`, or already linked to another Playbook Setup (1:1, `TRADEOS_DATABASE_DESIGN.md` Section 5.1) |
| `/api/v1/playbook-setups/{id}` | GET | Full detail, **including live performance** | Performance is fetched by this endpoint calling the Statistics module's by-dimension capability internally (Section 5.1's composition pattern) — never stored on the Playbook Setup itself (Domain Model Section 8.8) |
| `/api/v1/playbook-setups/{id}` | PATCH | Edit entry/exit criteria, ideal conditions, risk rules | |
| `/api/v1/playbook-setups/{id}/deprecate` | POST | Mark as no longer actively traded | Retained for historical attribution (Domain Model Section 13.4) |
| `/api/v1/playbook-setups/{id}/attachments` | POST | Add a screenshot/example reference | |
| `/api/v1/playbook-setups/{id}/attachments/{attachmentId}` | DELETE | Remove an attachment | Hard delete is acceptable here — an attachment is presentation content, not history (`TRADEOS_DATABASE_DESIGN.md` Section 6.16) |

### 6.9 Mistakes Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/mistakes/ranking` | GET | Frequency, total cost, and priority ranking per Mistake Tag | Computed on demand, every call (Domain Model KDD-04's "recompute, never cache as truth" posture) — no write endpoints exist in this module; tagging happens through the Trades module (Section 6.4) |

### 6.10 Statistics Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/statistics/overview` | GET | Win Rate, Expectancy, Profit Factor, Average R, Total P&L, average Engine scores, across all (non-deleted) Trades | |
| `/api/v1/statistics/by-dimension` | GET | Same metrics, grouped by `?dimension=strategy\|setup\|session\|direction` | |
| `/api/v1/statistics/rolling` | GET | Same metrics, computed over the most recent `?window=10\|20\|30\|50\|100\|200` Trades, alongside the all-time comparison | Mirrors the Excel's Rolling Statistics sheet and the already-built prototype exactly in shape, per `PROJECT_AUDIT.md` |

All three endpoints are pure reads with no side effects and no persisted result (Domain Invariant DI-11) — every call recomputes from `trading` data fresh.

### 6.11 Journal Module

#### `POST /api/v1/journal-entries`
- **Purpose:** create a new reflection, either trade-scoped or period-scoped.
- **Request Body:** `content` (required), and **exactly one of** `trade_id` OR (`period_start` AND `period_end`) — matching `TRADEOS_DATABASE_DESIGN.md` Section 6.17's check constraint exactly.
- **Status Codes:** `201`; `422` if both or neither reference type is supplied.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/journal-entries` | GET | List, filterable by `trade_id` or a date range overlapping `period_start`/`period_end` |
| `/api/v1/journal-entries/{id}` | GET | Single entry |
| `/api/v1/journal-entries/{id}` | PATCH | Edit content (the reference type/target is immutable after creation — changing what an entry is "about" is modeled as delete-and-recreate, not an edit, to avoid ambiguous history) |
| `/api/v1/journal-entries/{id}` | DELETE | Soft delete |

### 6.12 Dashboard Module

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/api/v1/dashboard` | GET | One response combining: Statistics overview, Rolling Statistics (default window), Mistakes ranking (top N), and the most recent few Trades | Pure composition (Section 5.1) — this endpoint contains no logic of its own beyond calling the other modules' already-specified capabilities and shaping one response |

---

## 7. Filtering, Sorting & Pagination

One consistent standard, applied identically to every list endpoint (`GET /trades`, `/journal-entries`, `/catalogs`, `/configuration/scoring-criteria`, etc.).

### 7.1 Filtering
Query parameters name the field directly (`?direction=long`, `?result=tp`, `?kind=setup`). Range filters use a `_after`/`_before` suffix for dates (`?entered_after=2026-01-01T00:00:00Z`) and `_min`/`_max` for numbers where applicable. Multiple filters combine with implicit `AND`.

### 7.2 Sorting
`?sort=field` for ascending, `?sort=-field` for descending (a leading `-`). Only one sort field is supported in v1 (multi-field sort is deferred until a real need appears, per Architectural Principle 4). Default sort, if omitted, is always the most business-meaningful recency field for that resource (`-entered_at` for Trades, `-created_at` elsewhere).

### 7.3 Searching
Free-text search (e.g., searching Trade notes) is **not implemented in v1** — no endpoint in Section 6 accepts a `?q=` parameter. Registered as Open Question API-1 (Section 18) rather than speculatively designed, since the Domain Model does not yet specify what "search" should mean across which fields.

### 7.4 Pagination
**Cursor-based**, for every list endpoint, including small ones (catalogs) — one consistent mechanism everywhere (API Design Principle 3, Section 2) rather than cursor for large collections and offset for small ones. Request: `?limit=50&cursor=<opaque_string>`. Response envelope:
```
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "<opaque_string_or_null>",
    "has_more": true
  }
}
```
`limit` defaults to 50, maximum 200 (a hardcoded ceiling, not user-configurable, to protect Section 15's performance posture). Offset-based pagination (`?page=2`) is deliberately not offered — it produces incorrect results under concurrent writes (a page boundary can skip or repeat a row if a Trade is inserted between two requests), which this API treats as a Correctness concern (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 9's top-ranked quality attribute) outranking the minor convenience offset pagination offers.

### 7.5 Field Selection
Not implemented in v1 (no `?fields=` parameter) — every response returns its full defined shape (Section 6). Considered premature optimization (Section 15) until a specific payload-size problem is demonstrated.

### 7.6 Expansion
Where a response could either embed a related resource or return only its ID, this document is explicit per-endpoint rather than offering a generic `?expand=` parameter (e.g., `GET /trades/{id}` always embeds the current Evaluation Snapshot summary, Section 6.4, because it's needed on nearly every view; it never embeds the full breakdown, which has its own endpoint). This keeps response shapes predictable (Section 1.4) rather than variable based on query parameters.

---

## 8. Error Model

One envelope, every error, every endpoint:

```
{
  "error": {
    "code": "<STABLE_MACHINE_READABLE_CODE>",
    "message": "<human-readable summary>",
    "details": [ { "field": "<optional>", "issue": "<optional>" } ],
    "trace_id": "<uuid, correlates to platform.event_log and server logs>",
    "timestamp": "<ISO 8601 UTC>"
  }
}
```

| Category | HTTP Status | Example `code` |
|---|---|---|
| Validation Errors | `422` | `VALIDATION_FAILED` |
| Business Errors (a Domain Invariant, `TRADEOS_DOMAIN_MODEL.md` Section 15) | `422` | `INVARIANT_VIOLATION` (with `details` naming which, e.g., `INV-TRADE-01`) |
| Authentication Errors | `401` | `UNAUTHENTICATED` |
| Authorization Errors | `403` (resource exists but isn't owned by caller — used only where revealing existence is itself not a leak; Section 6.4 prefers `404` for Trades specifically, Section 14) | `FORBIDDEN` |
| Not Found | `404` | `NOT_FOUND` |
| Conflict Errors (duplicate, wrong state for the action) | `409` | `CONFLICT` |
| Rate Limits | `429` | `RATE_LIMITED` |
| Unexpected Errors | `500` | `INTERNAL_ERROR` (message never leaks internal detail — the `trace_id` is the mechanism for the developer to investigate server-side, per Observability, `TRADEOS_SYSTEM_ARCHITECTURE.md` Architectural Principle 5) |

**Every business-error `code` traces to a specific Domain Invariant ID** (`TRADEOS_DOMAIN_MODEL.md` Section 15) wherever one exists, in the `details` array — this is the API-level realization of "every decision is traceable" applied to failure modes, not just successes.

---

## 9. Validation Rules

Validation is layered, and each layer's failures map to a specific error category (Section 8):

1. **Shape/format validation** (missing required field, wrong type, malformed date) → `VALIDATION_FAILED`, `422`.
2. **Value range validation** (e.g., `scoring_weights.weight >= 0`, `min_value <= max_value` on a criterion) → `VALIDATION_FAILED`, `422`.
3. **Business/domain invariant validation** (INV-TRADE-01, INV-TRADE-02, INV-CRITERION-02, etc., `TRADEOS_DOMAIN_MODEL.md` Section 15) → `INVARIANT_VIOLATION`, `422`.
4. **State/conflict validation** (closing an already-closed Trade, publishing an already-published configuration version) → `CONFLICT`, `409`.

**"Risk cannot exceed configured limits"** (named in the prompt) has **no corresponding Domain Model concept today** — `TRADEOS_DATABASE_DESIGN.md` already registered this territory as Open Question DB-3 ("Risk Profiles"). This document does not invent a validation rule for a concept that does not yet exist; it is carried forward as Open Question API-2 (Section 18), explicitly linked to DB-3, rather than answered independently and inconsistently here.

---

## 10. Long Running Operations

**There are none in v1.** Every endpoint in Section 6 completes synchronously within a single request/response cycle — including `POST /trades` (Section 6.4), which performs Evaluation inline (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 4's synchronous, same-transaction design, ADR-03). This is a deliberate consequence of the Modular Monolith and on-demand-Analytics decisions already frozen, not an oversight: nothing in the current system does enough work to justify async job semantics (progress polling, cancellation, retries).

**This will change** the moment a Future Reserved Domain requiring genuine background work is built — the clearest candidate is AI Coaching (`TRADEOS_DOMAIN_MODEL.md` Section 17) generating a response that may take longer than an interactive request should block for. When that happens, this section is the one to extend with a standard `202 Accepted` + polling (or webhook, Section 17) pattern — reserved conceptually here, not designed in detail now (Architectural Principle 4).

---

## 11. Event Integration

Every write endpoint's Domain Event (`TRADEOS_DOMAIN_MODEL.md` Section 11) is dispatched in-process, synchronously, within the same request (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 6.1) — the API caller never sees the event directly, but its occurrence is always durably logged (`platform.event_log`, `TRADEOS_DATABASE_DESIGN.md` Section 6.18) regardless of whether any module currently subscribes to it.

### 11.1 Illustrative Flow: `POST /trades`

```
POST /trades
  │
  ▼
Trading module validates INV-TRADE-01/02
  │ (fails → 422, no event)
  ▼ (passes)
Trading module calls Evaluation module synchronously
  │
  ▼
Evaluation module calls Configuration module for active weights/criteria
  │
  ▼
Evaluation module returns EvaluationSnapshot
  │
  ▼
Trading module persists Trade + ChecklistSnapshot + EvaluationSnapshot
  (one transaction)
  │
  ▼
Event dispatcher fires, in order: TradeRegistered → TradeEvaluated
  │
  ▼
201 response returned to caller, containing the full Trade + its Evaluation
```

No consumer currently subscribes to `TradeRegistered`/`TradeEvaluated` synchronously within this flow — they are logged for future consumers (Future Reserved Domains, `TRADEOS_DOMAIN_MODEL.md` Section 17) and for `platform.event_log`'s audit purpose (Section 8's `trace_id` correlates a request to its logged events).

### 11.1.1 Illustrative Flow: `POST /trades/{id}/open` *(new in v2.0)*
```
POST /trades/{id}/open
  │
  ▼
Trading module validates the Trade is Planned (INV-TRADE-04), transitions Planned → Open
  │
  ▼
Trading module calls Evaluation module synchronously (first time for this Trade —
  identical to the tail of POST /trades' own flow above)
  │
  ▼
Trading module persists Trade + ChecklistSnapshot + EvaluationSnapshot (one transaction)
  │
  ▼
Event dispatcher fires, in order: TradeOpened → TradeEvaluated
  │
  ▼
200 response returned to caller, containing the full Trade + its Evaluation
```

### 11.2 Illustrative Flow: `POST /trades/{id}/close`
```
POST /trades/{id}/close
  │
  ▼
Trading module validates INV-TRADE-02, transitions Open → Closed
  │
  ▼
Event dispatcher fires: TradeClosed
  │
  ▼
200 response returned
```
Nothing currently subscribes synchronously to `TradeClosed` either — it is the schema-confirmed seam (`TRADEOS_DATABASE_DESIGN.md` Section 12) a future Mistake Tracking ranking-refresh or Notification would attach to.

### 11.3 Illustrative Flow: `POST /configuration/versions/{id}/publish`
```
POST /configuration/versions/{id}/publish
  │
  ▼
Configuration module validates all referenced criteria are active
  │
  ▼
Previous published version → superseded; new version → published
  │
  ▼
Event dispatcher fires: ScoringConfigurationChanged
  │
  ▼
200 response returned
   (Note: NO automatic re-evaluation of existing Trades — that
    remains a separate, explicit per-Trade action, Section 6.4)
```

**The AI-recommendations-queued example given in the prompt** (`POST /trades → TradeCreated → EvaluationCalculated → AnalyticsUpdated → AIRecommendationsQueued`) **does not reflect this API's actual v1 behavior** and is not asserted here as if it did — `AnalyticsUpdated` is not a real event (Analytics recomputes on demand, Domain Invariant DI-11, it does not maintain state that needs "updating"), and `AIRecommendationsQueued` belongs to the not-yet-built AI Coaching domain (Section 17). This document corrects the example rather than silently adopting it, consistent with prioritizing accuracy over matching the prompt's illustration.

---

## 12. API Versioning

- **Current Version:** `v1`, covering every endpoint in Section 6.
- **Backward Compatibility:** within `v1`, only additive, non-breaking changes are permitted — a new optional field, a new endpoint, a new enum value in a response. Anything else requires a new version segment for the affected resource.
- **Deprecation Policy:** a deprecated `v1` endpoint remains functional and is marked in its documentation as deprecated, with the `v2` replacement named, for a defined overlap period before removal — the specific length of that period is **Open Question API-3** (Section 18), since it depends on how many clients exist, which itself depends on Product Bible Open Question 2. The states an endpoint moves through over this lifetime are formalized in Section 13.
- **Breaking Changes:** require a new version segment (`/api/v2/trades`), never an in-place change to `/api/v1/trades`'s existing contract.
- **Migration Strategy:** mirrors `TRADEOS_DATABASE_DESIGN.md` Section 13.3's expand/contract pattern — a new response field ships additively; a client migrates to reading it; only then is any old field ever removed, and only in a new version.

---

## 13. Endpoint Lifecycle

Every endpoint in this API moves through exactly four states over its lifetime. This section defines them once, formally, so no endpoint's stability expectations are ever ambiguous or negotiated ad hoc.

| State | Meaning | May the shape change without a new version? | Caller expectation |
|---|---|---|---|
| **Experimental** | Newly shipped; not yet proven correct under real use | Yes — shape may still change in a `v1`-compatible but non-additive way | Safe to build against for active development only; not recommended as a stable integration target |
| **Stable** | Proven correct in real operation; governed fully by Section 12's backward-compatibility rules from this point forward | No — only additive changes, per Section 12 | Safe to depend on indefinitely, within the current version |
| **Deprecated** | Still fully functional; a replacement already exists and is named | No (it is frozen, not evolving) | Should migrate to the named replacement before the overlap period (Open Question API-3, Section 18) ends |
| **Removed** | No longer callable | N/A | Returns `410 Gone` (not a bare `404`) for a defined grace period, so a caller can distinguish "this used to exist and was intentionally retired" from "this never existed" or "you mistyped the ID" — only after that grace period does it fall back to an ordinary `404` |

### 13.1 Current State of Every Endpoint in This Document
Every endpoint specified in Section 6 is, as of this freeze, **Experimental** — consistent with `PROJECT_AUDIT.md`'s Readiness Assessment (42%) and the fact that none of them has yet been implemented or exercised under real, sustained use (only two real historical Trades exist in the source Excel). Being written down in this canonical specification is a necessary condition for promotion to Stable, never a sufficient one — promotion happens per-endpoint, after real implementation and real use, not automatically at the moment a contract is frozen on paper.

### 13.2 Transition Rules
- **Experimental → Stable:** a judgment call made once an endpoint has been implemented and used in real operation for a period sufficient to have surfaced any shape problems — no fixed duration is mandated here (an Open Question, if a stricter rule is ever wanted).
- **Stable → Deprecated:** only once a named, available replacement exists — an endpoint is never deprecated into a void.
- **Deprecated → Removed:** only after the overlap period (Section 12) has elapsed.
- **No state is ever skipped.** An endpoint cannot go directly from Stable to Removed, even under time pressure — Section 1's "predictable behavior" principle applies to the API's own evolution, not only to any single request.

---

## 14. Security Considerations

- **Rate Limiting:** applied per authenticated user (not per IP, since the API requires authentication for nearly every endpoint) — specific thresholds are an operational tuning decision, not fixed in this document; the error shape (`429`, `RATE_LIMITED`, Section 8) is fixed now so clients can handle it uniformly regardless of the eventual threshold.
- **Input Validation:** every write endpoint's request body is validated per Section 9 before touching any domain logic — malformed input never reaches the Evaluation Engine or the database.
- **Output Sanitization:** free-text fields (`trades.notes`, `journal_entries.content`) are returned as stored, escaped appropriately by the frontend at render time (an API does not need to sanitize JSON string output the way it would HTML — this is a frontend responsibility, out of this document's scope).
- **Authorization / Ownership Validation:** every endpoint's implementation must apply Section 4.6's ownership rule before returning or mutating data — a resource that exists but isn't owned by the caller returns `404`, not `403`, for `Trades`/`JournalEntries` specifically (Section 8), to avoid confirming a given Trade ID exists at all to a non-owner.
- **Sensitive Data:** no endpoint in Section 6 ever returns `password_hash` (`TRADEOS_DATABASE_DESIGN.md` Section 11.1) — the Users module's response shape never includes it, under any circumstance, including to the resource's own owner.
- **Audit Logging:** every write is logged via the same Domain Event mechanism already described (Section 11) into `platform.event_log` — the API layer does not need a separate audit mechanism of its own.
- **Replay Protection:** refresh token rotation (Section 4.3) is the primary defense; `Idempotency-Key` (Section 3.6) additionally prevents a retried `POST /trades` from being misinterpreted as an intentional replay attack pattern rather than a network retry.
- **Future API Keys:** not implemented in v1 — there is no third-party or service-to-service caller yet (Section 17's Public API/Plugin SDK are the future consumers that would need them). Reserved, not designed.

---

## 15. Performance Considerations

- **Caching Opportunities:** `GET /configuration/*` and `GET /catalogs` responses change rarely and are strong candidates for short-TTL HTTP caching (`Cache-Control` headers) — a real, low-risk optimization, unlike a general Analytics cache (which `TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-04 explicitly defers).
- **Batch Operations:** not offered in v1 (no `POST /trades/batch`) — every write is single-resource, matching the current single-user, manual-entry-or-one-at-a-time-import usage pattern. Revisit only if a real bulk-import need appears (Section 17, future CSV/broker import).
- **Bulk Imports:** explicitly out of scope for v1 (`TRADEOS_PRODUCT_BIBLE.md` Section 11, Out of Scope: automated broker integration) — when built, this is a new, dedicated endpoint (or the Broker Integration domain's own upstream seam, `TRADEOS_SYSTEM_ARCHITECTURE.md` Section 13), not a retrofit onto `POST /trades`.
- **Lazy Loading:** the API's own "don't over-embed" stance (Section 7.6) is this API's version of lazy loading — a Trade's full evaluation breakdown, its journal entries, are separate calls, fetched only when a view actually needs them.
- **Compression:** standard HTTP response compression (gzip/brotli) is assumed at the infrastructure level (`TRADEOS_SYSTEM_ARCHITECTURE.md` Section 12), not something this API contract needs to specify itself.
- **Efficient Queries:** every filterable/sortable field named in Section 7 corresponds to an index already specified in `TRADEOS_DATABASE_DESIGN.md` Section 10.1 — this document did not introduce a filter option the database design hasn't already provisioned for.
- **Pagination:** covered fully in Section 7.4; restated here only to confirm it is treated as a performance requirement, not merely a convenience.

---

## 16. OpenAPI Readiness

Every endpoint in Section 6 already carries the structured information an OpenAPI document requires: a stable path, an HTTP method, authentication requirement, a fully-typed request body (Section 6's field lists, cross-referenced against `TRADEOS_DATABASE_DESIGN.md`'s column types for exact data types), a fully-typed response body, and an exhaustive status code list (cross-referenced against Section 8's error model). Converting this document into an OpenAPI 3.x specification is expected to be a mechanical transcription exercise, not a design exercise — any point where it is not mechanical (i.e., where an implementer must make a judgment call this document didn't already make) is a defect in this document, not an expected part of that future conversion, and should be raised as a correction to this document rather than silently resolved in the OpenAPI file.

---

## 17. Future API Extensions

Reserved, undesigned, consistent with `TRADEOS_DOMAIN_MODEL.md` Section 17 (Future Reserved Domains) and `TRADEOS_DATABASE_DESIGN.md` Section 12:

- **AI Coach:** a future `POST /ai/conversations`-style module, downstream-only (Section 11.3's `ScoringConfigurationChanged` and other events are exactly what it would consume), likely the first consumer of Section 10's Long Running Operations pattern (and, once built, the first endpoints to enter Section 13's Experimental state).
- **Broker Integrations / TradingView Synchronization:** would introduce a new upstream module supplying data to `POST /trades` (or a dedicated bulk-import variant, Section 15) — never a modification to the Trades module's existing contract.
- **Mobile App:** consumes the exact same `v1` API — no new endpoints implied, though may eventually motivate Section 7.5's Field Selection if payload size on mobile networks becomes a real, measured concern.
- **Plugin SDK / Public API / Webhooks / Marketplace:** all require API Keys (Section 14, deferred) and a service-to-service authentication model distinct from Section 4's user-token flow — reserved as a namespace and a known gap (Section 18), not designed now, since none has a corresponding Domain Model entity yet.

---

## 18. Known Gaps

| ID | Topic | Current State | Target State | Reason | Priority |
|---|---|---|---|---|---|
| API-1 | Free-text search | Not implemented — no `?q=` on any endpoint | A defined search capability (which fields, what matching semantics) | The Domain Model does not yet specify what "search" means across which fields | Low |
| API-2 | Risk-limit validation ("risk cannot exceed configured limits") | No corresponding Domain Model concept | Depends entirely on resolving `TRADEOS_DATABASE_DESIGN.md` Open Question DB-3 (Risk Profiles) first | Named in this document's source prompt; no upstream entity exists yet | Medium — same priority as DB-3, since they are the same underlying gap |
| API-3 | Deprecation overlap period length | Not specified | A concrete duration (e.g., 90 days) once there is more than one client to actually coordinate with | Depends on Product Bible Open Question 2 (is there ever more than one client/consumer?) | Low today, rising in priority the moment a second client exists |
| API-4 | "Trading Accounts" module | No corresponding Domain Model entity — `UserAccount` today implicitly represents one trader with one implicit account | A dedicated Account entity, if multi-account-per-user is ever a real requirement | Named in this document's source prompt; not modeled upstream | Low — conditional on a use case (e.g., separating a demo account from a live account) that has not been raised in any frozen document |
| API-5 | "Calendar" module | Same open question as `TRADEOS_DATABASE_DESIGN.md` DB-1 | Either a pure frontend view (no new endpoint) or a new entity requiring new endpoints | Carried forward, not re-litigated independently | Low |
| API-6 | Reports/Notifications modules | Reserved namespace only (Section 17) | Endpoints designed once their Domain Model entities exist | Consistent with not inventing business logic | Low |

---

## 19. Traceability Matrix

| Business Capability | API Module | Representative Endpoint | Domain Model | Database Module | Future Frontend Module |
|---|---|---|---|---|---|
| Register and score a trade | Trades, Evaluation | `POST /trades` | Trade, EvaluationSnapshot, ChecklistSnapshot (Domain Model §8.1–8.3) | `trading` (`TRADEOS_DATABASE_DESIGN.md` §6.9–6.13) | Trade entry form |
| Explain a historical score | Evaluation | `GET /trades/{id}/evaluation` | EvaluationSnapshot, CriterionBreakdownRow (§8.2, §9) | `trading.evaluation_snapshot_breakdowns` (§6.13) | Rule Explorer |
| Preview a score before saving | Evaluation | `POST /evaluation/preview` | EvaluationEngine domain service (§12.1) | *(no table — pure computation)* | Checklist live preview |
| Manage scoring configuration | Configuration | `POST /configuration/versions/{id}/publish` | ScoringConfiguration, ScoringCriterion, ScoringWeight (§8.4–8.6) | `configuration` (§6.3–6.7) | Configuration admin screen |
| Manage reference lists | Catalogs | `POST /catalogs/{id}/deactivate` | Catalog, CatalogEntry (§8.7) | `configuration.catalog_entries` (§6.8) | Settings / Catalog management |
| Document and track a setup | Playbook | `GET /playbook-setups/{id}` | PlaybookSetup (§8.8) | `playbook` (§6.15–6.16) | Playbook module |
| Understand recurring errors | Mistakes | `GET /mistakes/ranking` | MistakeTag, MistakePriorityRankingService (§8.9, §12.3) | *(no table — reads `trading` + `configuration`)* | Mistake Analytics |
| Understand performance | Statistics | `GET /statistics/by-dimension` | StatisticsAggregationService (§12.2) | *(no table — reads `trading` + `evaluation` data)* | Statistics / Rolling Statistics |
| Reflect qualitatively | Journal | `POST /journal-entries` | JournalEntry (§8.10) | `journal` (§6.17) | Journal module |
| Authenticate | Authentication, Users | `POST /auth/login` | UserAccount (§8.11) | `identity` (§6.1) | Login screen |
| Personalize the app | Preferences | `PATCH /preferences` | UserPreferences (§8.12) | `preferences` (§6.2) | Settings screen |
| One-screen overview | Dashboard | `GET /dashboard` | *(composition only, §5.1 — no dedicated entity)* | *(composition of the above)* | Dashboard |
| Confirm the process is alive (infrastructure, not a business capability) | Health Check | `GET /healthz` | *(none — §5.2, no Bounded Context)* | *(none — no data owned or read)* | N/A — consumed by hosting-platform infrastructure, never the frontend |

Every endpoint in Section 6 appears in, or is a variant of, a row above. Any future endpoint must be added as a new row before being implemented, per the same standard `TRADEOS_DATABASE_DESIGN.md` Section 15 and `TRADEOS_DOMAIN_MODEL.md` Section 18 already established.

---

## 20. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-24 | Initial API Specification. Derived from all five frozen foundational documents. Defined API philosophy, REST architecture, authentication/authorization model, 12 API modules, full endpoint specifications, a unified filtering/sorting/pagination standard, a unified error model, validation rules, an explicit "no Long Running Operations in v1" position, event integration flows (correcting the source prompt's illustrative example where it didn't match confirmed behavior), versioning policy, security and performance considerations, OpenAPI readiness, reserved future extensions, six known gaps, and a full traceability matrix. |
| 1.1 | 2026-07-24 | Approved and frozen as canonical. Added API Design Principles (Section 2, a concrete, tactical checklist distinct from Section 1's higher-level Philosophy) and Endpoint Lifecycle (Section 13, formalizing Experimental/Stable/Deprecated/Removed states and confirming every currently-specified endpoint starts Experimental). Renumbered all sections accordingly. |
| 1.2 | 2026-07-30 | Downstream of `TRADEOS_DOMAIN_MODEL.md` v2.0 (KDD-07) and `TRADEOS_DATABASE_DESIGN.md` v1.2. Section 6.4: `POST /trades` gains required `status` (`planned`\|`open`\|`closed`), with `entry_price`/`stop_loss`/`entered_at`/`scoring_profile` now conditionally required (absent while `status=planned`); `take_profit`/`margin_used` added as optional fields; `realized_pnl`/`closed_at` now required inputs of `status=closed`/`POST /trades/{id}/close` (previously never a client-supplied field); response gains computed `roi_percent`/`pnl_percent`. New endpoint `POST /trades/{id}/open` (Section 11.1.1) — the `Planned → Open` transition, firing `TradeOpened` and Evaluation for the first time. `GET /trades` gains `?status=` filtering; `result` no longer accepts `open` as a filter value. |
| 1.3 | 2026-08-05 | Resolves `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Open Question OQ-1 and `TRADEOS_BACKEND_BLUEPRINT.md` Known Gap BE-7, ahead of Phase 9 (Deployment & Production Hardening), Sprint 9.1, whose Exit Criteria cannot be verified without this contract existing. New Section 6.0: `GET /healthz` — a liveness-only endpoint (explicitly not a readiness/dependency check), unauthenticated, outside `/api/v1` versioning. New Section 5.2 explaining why it is cross-cutting infrastructure, not a Bounded Context. Section 3.2 amended to note this one exception to universal `/api/v1` versioning. Section 19 Traceability Matrix gains a row. No existing endpoint's contract changed. |

**Status:** FROZEN. This is the sixth permanent foundational document of TradeOS, after `PROJECT_AUDIT.md`, `TRADEOS_PRODUCT_BIBLE.md`, `TRADEOS_DOMAIN_MODEL.md`, `TRADEOS_SYSTEM_ARCHITECTURE.md`, and `TRADEOS_DATABASE_DESIGN.md`.
**Next document:** to be determined.
