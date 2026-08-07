# Changelog

All notable changes to TradeOS are recorded here, sprint by sprint, per
`docs/09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`.

## Sprint 0.1 — Backend Skeleton & Event Infrastructure

Phase 0 of the Implementation Master Plan. Scope: stand up the Modular
Monolith's module-folder structure (`TRADEOS_BACKEND_BLUEPRINT.md` §16) and
the in-process Domain Event dispatcher + `platform.event_log` writer.

### Added
- Backend project bootstrap (Poetry, Alembic, Docker Compose for
  PostgreSQL 16) per `TRADEOS_TECHNICAL_STACK.md`.
- Empty module-first scaffolding for all 9 Bounded Contexts (`identity`,
  `preferences`, `trading`, `evaluation`, `configuration`, `playbook`,
  `mistakes`, `statistics`, `journal`) plus `shared_kernel/`.
- `app/platform/` — in-process synchronous Domain Event dispatcher,
  `event_log` writer, and the `platform.event_log` table (migration
  `0001_create_platform_schema_and_event_log`), matching
  `TRADEOS_DATABASE_DESIGN.md` §6.18 exactly.
- `tests/platform/test_event_dispatcher.py` — proves Sprint 0.1's Exit
  Criteria against a real, ephemeral PostgreSQL instance (Testcontainers).

### Dependency note
`asyncpg` was pinned to `^0.31.0` instead of the originally planned
`^0.29.0`. **This is a compatibility fix, not an architectural or
technology decision:** `asyncpg 0.29.0` ships no prebuilt wheel for
Python 3.14 on Windows, and this development machine has no Microsoft
C++ Build Tools to compile it from source. `asyncpg 0.31.0` publishes a
`cp314-win_amd64` wheel and installs cleanly. SQLAlchemy 2.0 (async) with
the `asyncpg` driver, as mandated by `TRADEOS_TECHNICAL_STACK.md` §7,
is unchanged — only the pinned patch/minor version moved.

### Verification performed
- `poetry install` — 59 packages installed cleanly.
- `alembic upgrade head` — `platform.event_log` created; columns, primary
  key, and all 3 indexes confirmed via direct `psql` inspection.
- `pytest tests/platform/` — 1 passed.
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean, after correcting `get_db_session`'s return type
  (`AsyncSession` → `AsyncGenerator[AsyncSession, None]`).

### Deferred
- Sprint 0.2 (auth middleware, correlation IDs) and Sprint 0.3 (frontend
  application shell) — not part of this sprint, per the Master Plan.

## Sprint 0.2 — Auth Middleware & Correlation IDs

Phase 0 of the Implementation Master Plan. Scope: JWT verification at the
Presentation boundary and a correlation ID threaded through every log line
— approved scope also included, at minimum viable size, centralized
exception handling (`TRADEOS_BACKEND_BLUEPRINT.md` §12) to shape the
sprint's own 401 correctly. Explicitly excludes login, registration, users,
roles, and every business module (Phase 1+).

### Added
- `app/platform/context.py` — request-scoped correlation ID / user ID,
  built on `structlog.contextvars` (no second, parallel contextvars
  mechanism).
- `app/platform/logging.py` — `structlog` configuration (JSON, correlation-
  ID bound via `merge_contextvars`), per `TRADEOS_TECHNICAL_STACK.md` §7.
- `app/platform/errors.py` — the one error envelope
  (`TRADEOS_API_SPECIFICATION.md` §8), `AppError`, and a minimal
  `register_exception_handlers()` (`AppError` + catch-all 500 only — no
  domain-invariant or business-validation handling, since no Use Cases
  exist yet).
- `app/platform/security/jwt.py` — `create_access_token` /
  `decode_access_token`, access tokens only (no refresh tokens, no
  password hashing). `create_access_token` is reusable infrastructure for
  the future Login Use Case (Phase 1) — not exposed by any endpoint here.
- `app/platform/security/dependencies.py` — `get_current_user_id`
  dependency for future routes.
- `app/platform/middleware/correlation_id.py`,
  `app/platform/middleware/authentication.py` — plain ASGI middleware
  (not Starlette's `BaseHTTPMiddleware`; see Implementation note).
- `tests/platform/test_jwt.py`,
  `tests/platform/test_authentication_middleware.py`,
  `tests/platform/test_correlation_id_middleware.py` — prove Sprint 0.2's
  Exit Criteria, including that a 401-rejected request is still
  correlation-ID bound.

### Modified
- `app/platform/config.py`, `.env.example` — added `jwt_secret_key`,
  `jwt_algorithm`, `jwt_access_token_expire_minutes`.
- `app/main.py` — wires `configure_logging()`, `register_exception_handlers()`,
  and both middleware (added in an order that makes `CorrelationIdMiddleware`
  outermost — see Implementation note).

### Implementation notes (not architectural decisions)
- **Plain ASGI middleware, not `BaseHTTPMiddleware`:** `BaseHTTPMiddleware`
  runs the downstream app in a separate `anyio` task, which does not
  reliably propagate contextvars set beforehand. Plain ASGI keeps the
  whole request in one call stack/task, so the bound `correlation_id` is
  guaranteed visible everywhere downstream, including inside a 401
  response. This is an implementation detail of "wire JWT verification /
  thread a correlation ID," not a deviation from anything the frozen docs
  specify.
- **Auth middleware builds its 401 response directly**, rather than
  raising and relying on the registered exception handlers: exceptions
  raised inside ASGI middleware run outside Starlette's
  `ExceptionMiddleware` layer and are never delivered to
  `@app.exception_handler`-registered handlers. Both paths use the same
  `build_error_envelope()` helper, so the shape is identical either way.
- **`# type: ignore[import-untyped]` on the `python-jose` import**
  (`app/platform/security/jwt.py`), instead of adding the `types-python-jose`
  stub package. `python-jose` itself is already in the Technical Stack
  (§7); its stub package is not, and is dev-tooling-only (never imported
  at runtime) — adding it felt like exactly the kind of unapproved
  addition the sprint's rules were guarding against, so a type-check
  suppression was used instead.
- **`structlog.testing.capture_logs()` strips the entire processor chain**
  (including `merge_contextvars`), so it cannot capture bound context
  values by design. The correlation-ID tests use a small local helper
  (`capture_logs_with_context()`) that reproduces `capture_logs()`'s
  capture mechanism while keeping `merge_contextvars` in the chain — a
  test-only fix, no production code affected.

### Verification performed
- `pytest tests/` — 14 passed (5 new JWT unit tests, 4 new authentication
  middleware tests, 4 new correlation-ID tests, 1 carried over from
  Sprint 0.1).
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean.
- No dependency changes — `python-jose` and `structlog` were already
  present from Sprint 0.1; `poetry install` was not re-run.

### Deferred
- Login, registration, refresh tokens, users, roles, and every business
  module (Phase 1+) — untouched, per approved scope.
- Health endpoint — confirmed out of scope; `TRADEOS_BACKEND_BLUEPRINT.md`
  §11 registers it as Open Question BE-7, explicitly deferred to
  Sprint 9.1 by the Master Plan.

## Sprint 0.3 — Frontend Application Shell

Phase 0 of the Implementation Master Plan. Scope: routing skeleton, the API
client layer, the standard error-envelope handling path, and design system
tokens (dark theme only) — `TRADEOS_FRONTEND_BLUEPRINT.md` §2.2, §2.8, §14.
No feature logic; `frontend/` was built from zero (confirmed empty at
sprint start).

### Added
- Frontend project bootstrap (Vite, React 18, TypeScript strict, Tailwind
  CSS fully configured, ESLint + Prettier) per `TRADEOS_TECHNICAL_STACK.md`
  §6, §9, §11.
- `src/design-system/tokens.css` + `tailwind.config.ts` — dark-theme-only
  color/elevation tokens (`TRADEOS_FRONTEND_BLUEPRINT.md` §14), consumed
  by Tailwind's config rather than hardcoded per component.
- `src/api/errors.ts` (`ApiError`, `parseApiError`, `networkError`) +
  `src/api/client.ts` — the API client layer
  (`TRADEOS_FRONTEND_BLUEPRINT.md` §2.2); only the generic request
  primitive and error normalization exist, no concrete endpoint function
  yet.
- `src/components/ErrorBanner.tsx` + `src/components/ErrorContext.tsx` —
  the one shared error path (§2.8, §17): any future feature module reports
  a failure via `useErrorReporter()`, rendered from exactly one place.
- `src/layout/AppShell.tsx`, `Sidebar.tsx`, `navigation.ts` — sidebar
  grouped Workspace/Analytics/Configuration per §4.1, including the
  visually-present-but-inactive "AI Coach" entry §4.1 explicitly requires.
- `src/router.tsx` + one placeholder page per confirmed frontend module
  (`TRADEOS_FRONTEND_BLUEPRINT.md` §3): Authentication, Dashboard, Trading,
  Evaluation, Configuration, Playbook, Mistakes, Statistics, Journal,
  Settings — 10 modules, one route each. Authentication has no sidebar
  entry (§5.7) and renders outside `AppShell`.
- `src/api/errors.test.ts` — Vitest unit tests for `parseApiError`'s
  normalization logic (pure functions, no component rendering).
- `e2e/error-banner.spec.ts` + `playwright.config.ts` — one Playwright E2E
  test proving the Exit Criteria: a simulated error renders through
  `ErrorBanner` identically from two different routes.
- `src/test-support/errorSimulation.ts` — a dev/test-only hook
  (`window.__tradeosSimulateApiError`) the E2E test calls, since no real
  endpoint exists yet to trigger a genuine failure. Guarded by
  `import.meta.env.DEV`, tree-shaken out of the production build.

### Implementation notes (not architectural decisions)
- **`@testing-library/react` was not added**, per your explicit decision:
  Vitest covers `parseApiError`'s pure logic only; Playwright (already in
  the Technical Stack) covers the actual rendering proof.
- **TanStack Query was not installed** — confirmed out of scope; arrives
  with the first feature that consumes real server data (Phase 1+).
- **`@types/node` added** (dev-only) — `playwright.config.ts` reads
  `process.env.CI`, which needs Node's type definitions to type-check.
  Node.js itself is already in the Technical Stack (§9); this is only its
  types, not a new runtime dependency.
- **pnpm's build-script approval** (`pnpm-workspace.yaml`,
  `allowBuilds: { esbuild: true }`) — pnpm 11 blocks postinstall scripts
  by default; `esbuild` is Vite's own transitive dependency, not a new
  technology, so its build script was explicitly allowlisted rather than
  silently skipped (which would leave Vite partially broken).
- **Settings' sidebar placement** — `TRADEOS_FRONTEND_BLUEPRINT.md` §4.1
  doesn't explicitly group "Settings" among Workspace/Analytics/
  Configuration, nor does it say "no sidebar entry" the way it does for
  Login/Register (§5.7). Given every other confirmed module in §4.1 does
  get a sidebar entry, Settings was placed as its own minimal group rather
  than omitted — a reasonable reading, not an explicit document
  instruction, flagged here for visibility.

### Verification performed
- `pnpm install` — 438 packages installed cleanly (after allowlisting
  `esbuild`'s build script).
- `pnpm typecheck` (`tsc -b --noEmit`) — clean, after adding `@types/node`.
- `pnpm lint` (ESLint) — clean, after fixing one `react/no-unescaped-entities`
  violation in `PlaceholderPage.tsx`.
- `pnpm format:check` (Prettier) — clean.
- `pnpm test` (Vitest) — 5 passed.
- `pnpm build` (`tsc -b && vite build`) — succeeded; `dist/` output
  169.98 kB JS / 7.40 kB CSS (gzip 55.42 kB / 2.11 kB).
- `pnpm test:e2e` (Playwright, Chromium) — 2 passed.

### Deferred
- Every module's real page content, forms, tables, charts — Phase 1+.
- TanStack Query, Radix UI, React Hook Form, Zod, Recharts, TanStack
  Table, date-fns, Sonner, lucide-react — all tied to features this
  sprint explicitly excludes.
- Theme switching (light theme) — dark is the only theme designed in
  detail today (§14); `class="dark"` is applied statically, no
  `UserPreferences`-driven toggle yet (that's Settings' real
  implementation, Phase 1).

### Post-approval quality review
A dedicated pass for dead code, placeholder consistency, HTTP-contract
isolation, and unused Design System tokens, requested before commit:

- **Unused tokens found and fixed:** `--color-accent`, `--color-warning`,
  and `--color-success` were defined in `tokens.css` and mapped in
  `tailwind.config.ts`, but no component actually used any of them as a
  Tailwind class. Fixed two ways — `accent` was given a real, current
  consumer (the active-nav-link indicator in `Sidebar.tsx`, a left
  border); `warning`/`success` were removed entirely, since nothing in
  Sprint 0.3's shell-only scope needs profit/loss/warning semantics yet
  (no forms, no P&L display, no toasts). They get added when a real
  consumer exists, not speculatively.
- **HTTP-contract isolation confirmed:** `fetch()`, the API base URL, and
  the raw (`snake_case`) error envelope shape appear only in
  `src/api/client.ts`, `src/api/errors.ts`, and their own test files.
  Every UI component (`ErrorBanner`, `ErrorContext`, pages, layout) only
  ever touches the already-normalized `ApiError` class
  (`error.code`/`error.message`/`error.traceId`), never the wire format.
  One narrow, documented exception: `src/test-support/errorSimulation.ts`
  constructs a simulated envelope so the E2E test can exercise the real
  `parseApiError` path end to end — it is test scaffolding, not a UI
  component, and it calls the real parser rather than bypassing it.
- **Placeholder consistency confirmed:** all 10 module pages are
  structurally identical — each imports and renders the same
  `PlaceholderPage` component with only its `title` prop differing.
- **No dead files/imports found** beyond one expected case:
  `src/api/client.ts` (the API client layer) has no current caller, since
  no feature module exists yet to call it — this is the sprint's own
  explicit deliverable ("the API client layer"), not leftover code, the
  same status `create_access_token` had after Sprint 0.2.
- Re-ran `pnpm lint`, `pnpm typecheck`, `pnpm test` (5 passed), and
  `pnpm build` after the token fix — all clean. Also re-ran
  `pnpm test:e2e` (2 passed) since `Sidebar.tsx` was touched, though not
  explicitly requested.

## Sprint 1.1 — Identity Backend

Phase 1 of the Implementation Master Plan. Scope: Register/Login/Refresh/Logout
Use Cases (`TRADEOS_BACKEND_BLUEPRINT.md` §4.8) and the `identity.user_accounts`
table (`TRADEOS_DATABASE_DESIGN.md` §6.1) — backend only; Preferences and the
Login/Register frontend pages are Sprint 1.2, untouched here.

### `identity.refresh_tokens` — a documented, approved extension of the frozen schema

**This is the most consequential decision of this sprint, so it is
recorded here in full.** `TRADEOS_API_SPECIFICATION.md` §4.3 requires
refresh tokens to be:
- issued alongside the access token at login,
- **single-use** (exchanging one invalidates it and issues a new one —
  rotation),
- **revocable server-side** (to support `POST /auth/logout`).

All three properties are impossible to implement without persisting
refresh-token state somewhere. `TRADEOS_DATABASE_DESIGN.md` — the frozen,
canonical schema document — defines only `identity.user_accounts` for the
`identity` schema; it names no table for refresh tokens anywhere. This was
identified as a genuine documentation omission (not a signal to build
stateless refresh tokens) and confirmed explicitly by the user before any
code was written.

**Resolution:** `identity.refresh_tokens` was added via migration `0002`,
following the exact conventions `TRADEOS_DATABASE_DESIGN.md` §6.1 already
establishes for `user_accounts` (application-generated UUID primary key,
`TIMESTAMPTZ` throughout, and — mirroring `password_hash`, never
`password` — a `token_hash` column that stores only a hash of the token,
never the raw secret):

```
identity.refresh_tokens
  id            UUID PK
  user_id       UUID NOT NULL REFERENCES identity.user_accounts(id)
  token_hash    VARCHAR(255) NOT NULL UNIQUE
  issued_at     TIMESTAMPTZ NOT NULL DEFAULT now()
  expires_at    TIMESTAMPTZ NOT NULL
  revoked_at    TIMESTAMPTZ NULL
```

All refresh-token logic (hashing, rotation, revocation, the repository)
lives entirely inside `app/modules/identity/` — no other module imports or
knows about any of it.

### Added
- `app/modules/identity/domain/user_account.py`, `refresh_token.py` —
  `UserAccount` (Domain Model §8.11) and `RefreshToken` (with `is_valid()`/
  `revoke()` domain logic, unit-tested without a database).
- `app/modules/identity/infrastructure/models.py` — `UserAccountModel`,
  `RefreshTokenModel`, using SQLAlchemy 2.0's typed `Mapped`/`mapped_column`
  style (see Implementation notes).
- `app/modules/identity/infrastructure/password_hasher.py` — Argon2id
  (`TRADEOS_TECHNICAL_STACK.md` §7.2).
- `app/modules/identity/infrastructure/token_hasher.py` — SHA-256 for
  refresh-token lookup hashing, deliberately not Argon2id (see
  Implementation notes).
- `app/modules/identity/infrastructure/repository.py` —
  `UserAccountRepository`, `RefreshTokenRepository`.
- `app/modules/identity/application/register.py`, `login.py`, `refresh.py`,
  `logout.py`, `token_issuance.py` — the four Use Cases plus a shared
  token-pair-issuance helper (used by both Login and Refresh, so issuance
  is never duplicated).
- `app/modules/identity/presentation/schemas.py`, `router.py` — the four
  endpoints, matching `TRADEOS_API_SPECIFICATION.md` §6.1 field-for-field.
- `alembic/versions/0002_create_identity_schema.py` — the `identity`
  schema, both tables.
- `tests/identity/` — unit tests (password hashing, token hashing,
  `RefreshToken.is_valid()`) and `test_auth_flow.py`, an integration test
  running the real FastAPI app (middleware included) against a real
  Postgres instance: the full Register→Login→Refresh→Logout flow, the
  Master Plan's own named regression test ("refresh-token rotation reuse
  is rejected"), logout revocation, duplicate-email 409, identical
  wrong-password/unknown-email 401, and password-never-in-response.

### Modified
- `app/platform/errors.py` — added `ConflictError` (409) and a
  `RequestValidationError` handler (422, `VALIDATION_FAILED`, reshaping
  FastAPI/Pydantic's own error body into the one envelope). Both are
  generic, cross-cutting infrastructure — neither reveals anything about
  refresh-token internals — needed now because Sprint 1.1 is the first
  sprint with real request bodies and real business-conflict cases to
  report.
- `app/platform/config.py`, `.env.example` — added
  `refresh_token_expire_days` (default 30 — see Implementation notes).
- `app/main.py` — registers the Identity router at `/api/v1`; added
  `/api/v1/auth/register`, `/login`, `/refresh` to
  `AuthenticationMiddleware`'s `public_paths` (designed for exactly this
  in Sprint 0.2) — `/auth/logout` deliberately excluded, since it requires
  a valid access token.
- `alembic/env.py`, `tests/conftest.py` — import Identity's models and
  create the `identity` schema alongside `platform`.
- `pyproject.toml` — `pydantic` now installed with its `email` extra
  (`email-validator`), needed for `EmailStr`. Approved as dependency
  support for already-mandatory Pydantic, not a new technology decision.

### Implementation decisions (documented per your instructions, not silently made)
- **Password minimum length: 8 characters.** `TRADEOS_API_SPECIFICATION.md`
  §6.1 says "minimum length per Section 9 validation rules," but §9 never
  states a concrete number. 8 is a temporary implementation default,
  applied via Pydantic's `Field(min_length=8)` — **to be replaced once the
  specification states a value explicitly**, not treated as a permanent
  answer.
- **Refresh token expiry: 30 days**, and **access token expiry: 30
  minutes** (unchanged from Sprint 0.2). `TRADEOS_API_SPECIFICATION.md`
  §4.1 requires a refresh token to be "longer-lived" than the access token
  but gives no exact durations for either.
- **Logout's interpretation:** `POST /auth/logout`'s contract
  (`TRADEOS_API_SPECIFICATION.md` §6.1) has no request body — the only
  data available is the authenticated caller's `user_id`. Since a user can
  hold more than one active refresh token (multiple devices/tabs) and the
  contract gives no way to identify one specific session, logout is
  implemented as "revoke every currently-active refresh token for this
  user." This is an interpretation, not a literal instruction — no frozen
  document resolves this ambiguity either way.
- **`token_hash` uses SHA-256, not Argon2id.** Argon2id is correct for
  password *verification* (compare a plaintext against one known stored
  hash) but unsuited to refresh-token *lookup* (`SELECT ... WHERE
  token_hash = ?`), which requires a deterministic digest — Argon2id's
  per-call random salt makes the same input hash differently every time.
  SHA-256 (Python's stdlib `hashlib`, no new dependency) is the standard,
  correct tool for this different problem.
- **SQLAlchemy models use the typed `Mapped`/`mapped_column` style**
  (SQLAlchemy 2.0), not the legacy `Column(...)` style Sprint 0.1's
  `EventLog` model uses. This was a real `mypy` finding, not a stylistic
  preference: the legacy style is untyped from mypy's perspective, and
  `repository.py` reads rows straight back into strictly-typed domain
  dataclasses, which the legacy style cannot satisfy. `EventLog` itself
  was left unchanged (out of this sprint's scope; it never hits the same
  typed round-trip).

### Verification performed
- `poetry lock` / `poetry install` — `email-validator` + `dnspython`
  installed cleanly (transitive, via Pydantic's `email` extra).
- `alembic upgrade head` — `0001 -> 0002` applied; both tables confirmed
  via direct `psql` inspection (columns, PK, unique indexes, FK).
- `pytest tests/` — **31 passed** (17 new: 8 integration + 9 unit; 14
  carried over from Sprints 0.1–0.2). No regressions.
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean, after the `Mapped`/`mapped_column` fix.

### Deferred
- `UserPreferences`, Login/Register frontend pages, Settings — Preferences
  page (Sprint 1.2).
- Roles/permissions, multi-session-aware logout, Domain Events for
  Identity actions (`BE-1`, already registered as accepted-as-is by the
  Master Plan) — none part of this sprint's approved scope.

## Sprint 1.2 — Preferences Backend/Frontend & Authentication Frontend

Phase 1 of the Implementation Master Plan. Scope: the Preferences module
(`GET`/`PATCH /preferences`, `TRADEOS_API_SPECIFICATION.md` §6.3;
`identity.user_preferences` per `TRADEOS_DATABASE_DESIGN.md` §6.2) plus the
first real frontend feature slice — Login/Register pages and a
Settings → Preferences page — the Master Plan's own "first fully vertical
(frontend-to-database) slice."

### Decisions approved before implementation (documented per your instructions)

- **`UserPreferences` auto-creation at registration (approved option a):**
  `RegisterUseCase` (Identity) now also creates the new user's default
  preferences, in the same transaction as the `UserAccount` insert, by
  calling a Use Case published from Preferences' own Application layer
  (`build_create_default_preferences_use_case(session)` —
  `app/modules/preferences/application/create_default_preferences.py`).
  This is an implementation decision, not something the frozen documents
  state directly: `TRADEOS_API_SPECIFICATION.md` §6.3 requires preferences
  to exist "automatically... at registration," but
  `TRADEOS_DOMAIN_MODEL.md` §11 defines no `UserRegistered` Domain Event
  for Preferences to react to asynchronously instead. Given no event
  exists to hook into, a synchronous same-transaction call was used,
  mirroring the already-established Trading → Evaluation pattern
  (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03). Module-boundary rule
  preserved: Identity imports only Preferences' Application-layer factory,
  never its Infrastructure or Domain layers directly (§3.3, Forbidden
  Dependencies).
- **Token storage: `localStorage` for both access and refresh tokens**
  (`frontend/src/auth/tokenStorage.ts`). Forced by the already-frozen API
  contract: `TRADEOS_API_SPECIFICATION.md` §4.3 returns the refresh token
  in the `POST /auth/refresh` JSON *body*, not an httpOnly cookie, so the
  client must be able to read it back with JavaScript to resubmit it —
  ruling out the httpOnly-cookie pattern regardless of preference. **This
  must be revisited if the API's refresh contract ever changes to a
  cookie-based flow.**
- **No automatic refresh-on-401 interceptor this sprint.** `api/client.ts`
  only attaches `Authorization: Bearer <token>` when an access token is
  present; a caller whose token has expired simply sees the 401. Automatic
  refresh retry is deferred, not implemented partially.
- **Milestone M1 (liveness endpoint, TLS) not blocking this sprint.**
  Both belong to later phases per the Master Plan's own planning
  (liveness: `TRADEOS_BACKEND_BLUEPRINT.md` §11, Open Question BE-7,
  deferred to Sprint 9.1; TLS: infrastructure/deployment concern, no
  sprint in Phase 0–1 owns it). Sprint 1.2 does not implement either.
- **Settings scope: Preferences only.** No Profile page, no Users page, no
  advanced notification configuration — all explicitly out of scope.
- **`notification_settings` persisted, no UI.** The column and domain
  field exist (`JSONB`, defaults to `{}`) and round-trip through
  `GET`/`PATCH /preferences`, but no frontend control renders it — the
  Domain Model does not yet define its shape, so no interface bound to an
  undefined thing was implemented.
- **Login and Register are two separate routes** (`/login`, `/register`),
  each with its own form and its own Zod schema, rather than a single
  toggling form.
- **Frontend dependencies:** TanStack Query, React Hook Form, Zod, Radix
  UI (`@radix-ui/react-select`, `@radix-ui/react-label`) — all already
  named in `TRADEOS_TECHNICAL_STACK.md` §6.3–§6.5; no other technology was
  added.

### Added
- `app/modules/preferences/domain/user_preferences.py` — `UserPreferences`
  dataclass (`TRADEOS_DOMAIN_MODEL.md` §8.12): `theme="dark"`,
  `language="es"`, `notification_settings: dict` (own `default_factory`,
  not shared across instances).
- `app/modules/preferences/infrastructure/models.py`,
  `repository.py` — `UserPreferencesModel` (schema `preferences`, typed
  `Mapped`/`mapped_column`, cross-schema FK to `identity.user_accounts.id`
  exactly as `TRADEOS_DATABASE_DESIGN.md` §6.2 specifies) and
  `UserPreferencesRepository` (single-row point queries only — no N+1).
- `app/modules/preferences/application/` — `CreateDefaultPreferencesUseCase`
  (+ its cross-module factory), `GetPreferencesUseCase`,
  `UpdatePreferencesUseCase` (partial update — only supplied fields
  change). `Get`/`UpdatePreferencesUseCase` raise a plain `RuntimeError`
  (surfacing as an unhandled 500, not a documented 404) if preferences are
  missing for an authenticated user — §6.3 guarantees this endpoint "never
  404s," so reaching that branch means the registration invariant itself
  was violated, a genuine bug rather than an expected condition.
- `app/modules/preferences/presentation/schemas.py`, `router.py` —
  `GET`/`PATCH /preferences`, both behind `get_current_user_id` (auth
  required, §6.3).
- `alembic/versions/0003_create_preferences_schema.py` — `preferences`
  schema and `user_preferences` table, matching §6.2 with no extension
  needed (unlike Sprint 1.1's `refresh_tokens`).
- `tests/preferences/` — 2 domain unit tests (defaults; mutable-default
  isolation) + 8 integration tests (auto-creation at registration,
  never-404s, 401 without auth, `PATCH` updates theme/language, partial
  `PATCH` preserves untouched fields, invalid enum → 422, two users have
  independent preferences).
- `frontend/src/auth/tokenStorage.ts`, `AuthContext.tsx`,
  `ProtectedRoute.tsx` — localStorage-backed session persistence (plain
  functions, not a hook, since `api/client.ts` needs to read the current
  token outside React) and a Context mirroring Sprint 0.3's
  `ErrorContext` pattern (`TRADEOS_TECHNICAL_STACK.md` §6.3: UI state is
  plain Context, no library).
- `frontend/src/features/authentication/` — `api.ts`, `schemas.ts`
  (Zod, password `min(8)` on register), `pages/LoginPage.tsx`,
  `pages/RegisterPage.tsx` (React Hook Form + Zod + TanStack `useMutation`).
- `frontend/src/features/settings/` — `api.ts`,
  `pages/PreferencesPage.tsx` (TanStack `useQuery`/`useMutation` + two
  Radix `Select`s for theme/language).
- `frontend/src/components/Select.tsx` — reusable Radix-based `Select`.
- `frontend/e2e/auth-and-preferences.spec.ts` — the Master Plan's own
  named Phase 1 E2E test ("register, log in, change a preference"): full
  vertical-slice flow plus an unauthenticated-redirect test. Requires the
  real backend running (documented in the file's own docstring — not
  automated by `playwright.config.ts`'s `webServer`, which manages only
  the Vite dev server; see Implementation notes).
- `frontend/src/auth/tokenStorage.test.ts`,
  `features/authentication/schemas.test.ts` — 9 new Vitest tests.

### Modified
- `app/modules/identity/application/register.py`,
  `presentation/router.py` — wire `CreateDefaultPreferencesUseCase` into
  registration (see Decisions above).
- `app/main.py` — registers `preferences_router`; adds `CORSMiddleware`
  (see Bugs found and fixed).
- `app/platform/config.py` — added `cors_allowed_origins` (default
  `["http://localhost:5173"]`, matching Vite's dev port). No frozen
  document specifies CORS — it is a pure browser cross-origin mechanism
  (`TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1: frontend and backend are served
  independently, i.e. cross-origin by construction), not an
  architectural/domain decision, so it was added without stopping to ask.
- `alembic/env.py`, `tests/conftest.py` — import Preferences' models;
  create the `preferences` schema alongside `platform`/`identity`.
- `frontend/src/api/client.ts` — attaches `Authorization: Bearer <token>`
  automatically when present.
- `frontend/src/App.tsx` — added `QueryClientProvider` (module-level
  singleton `QueryClient`) and `AuthProvider`.
- `frontend/src/router.tsx` — added `/register`; wrapped `AppShell` in
  `<ProtectedRoute>`; replaced the Sprint 0.3 `AuthenticationPage`/
  `SettingsPage` placeholders with `LoginPage`/`RegisterPage`/
  `PreferencesPage` (placeholders deleted, not left dead).
- `frontend/package.json` — added the four approved dependencies listed
  above.

### Bugs found and fixed (during this sprint's own verification, before commit)
- **CORS preflight 405:** the first real cross-stack E2E run showed
  `OPTIONS /api/v1/auth/register` → `405 Method Not Allowed` — no
  `CORSMiddleware` existed to answer the browser's preflight. **Fix:**
  added `CORSMiddleware` as the *outermost* middleware in `app/main.py`
  (Starlette runs the last-added middleware first/outermost).
  `AuthenticationMiddleware` must not run before `CORSMiddleware`: a
  cross-origin preflight never carries `Authorization`, so if
  Authentication ran first it would reject every preflight with 401
  before CORS ever got to answer it. Verified via a direct `curl -X
  OPTIONS ... -H "Origin: http://localhost:5173"` returning 200, and by
  re-running the full backend `pytest` suite (46/46, no regressions to
  Sprint 0.2's correlation-ID/auth-rejection guarantees).
- **Playwright assertion false failure:** `toHaveText("Dark")` failed
  against the Radix `Select` trigger, whose accessible text also includes
  the decorative "▾" icon (`"Dark▾"`). **Fix:** changed the three
  affected assertions to `toContainText`.

### Implementation notes (not architectural decisions)
- **Vitest has no `localStorage`** (`environment: "node"`, per Sprint
  0.3's `vite.config.ts` and the Technical Stack's Vitest-only mandate).
  `tokenStorage.test.ts` installs a minimal in-memory `Storage`-shaped
  mock via `beforeAll` in the test file itself, rather than adding
  `jsdom` as a new dependency — keeping this sprint's dependency additions
  to exactly the four approved ones.
- **The cross-stack E2E test's backend prerequisite is manual, not
  automated.** `playwright.config.ts`'s `webServer` manages only the Vite
  dev server (Sprint 0.3); wiring it to also start FastAPI + a migrated
  Postgres instance is CI/tooling infrastructure work with no frozen-doc
  mandate this sprint, so it was left as a documented prerequisite in the
  spec file's own docstring instead of built.

### Verification performed
- `docker compose down -v && up -d` + `alembic upgrade head` from an
  empty database — `0001 → 0002 → 0003` all applied cleanly in sequence.
- `pytest tests/` — **46 passed** (10 new: 8 integration + 2 unit; 36
  carried over from Sprints 0.1–1.1). No regressions, re-confirmed again
  after the CORS fix and again against the freshly-migrated database.
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean (85 source files).
- `pnpm lint` (ESLint), `pnpm typecheck` (`tsc -b --noEmit`),
  `pnpm format:check` — clean.
- `pnpm test` (Vitest) — **14 passed** (5 carried over from Sprint 0.3 + 3
  `tokenStorage` + 6 `schemas`).
- `pnpm build` — succeeded (400.09 kB JS / 8.64 kB CSS).
- `pnpm test:e2e` (Playwright) — **4 passed** (2 carried over from Sprint
  0.3 + the new full auth+preferences vertical-slice flow +
  unauthenticated-redirect), against the real backend + freshly-migrated
  database.
- Audit pass (mirroring Sprint 1.1's): no secrets in logs/errors/exception
  bodies (tokens/passwords never logged; `RuntimeError` messages carry
  only a `user_id`, never a credential); `GET`/`PATCH /preferences`
  response shapes verified field-for-field against §6.3; Identity →
  Preferences dependency confirmed one-directional (Preferences never
  imports Identity); no N+1 queries (repository methods are single-row
  point lookups/updates); no dead code, unused imports, or
  TODO/FIXME/HACK markers found in any file added or modified this
  sprint; no leftover references to the deleted `AuthenticationPage`/
  `SettingsPage` placeholders.

### Deferred
- Automatic refresh-on-401 retry, Profile/Users pages, advanced
  notification settings UI, light-theme visual implementation, liveness
  endpoint, TLS — all explicitly out of this sprint's approved scope (see
  Decisions above).
- Automating the E2E backend prerequisite in `playwright.config.ts` — left
  as documented manual setup.

## Sprint 2.1 — Configuration Backend

Phase 2 of the Implementation Master Plan, the first sprint of Configuration
— per `TRADEOS_DOMAIN_MODEL.md` §4.3, "the most upstream Bounded Context":
`ScoringCriterion`/`ScoringWeight`/`ScoringConfigurationVersion` CRUD,
`PublishScoringConfigurationVersion`, and a first published configuration
version seeded from real data. Catalogs (`TRADEOS_API_SPECIFICATION.md`
§6.7) is Sprint 2.2, not touched here, even though it shares this same
`configuration` Postgres schema (`TRADEOS_BACKEND_BLUEPRINT.md` §3.6).

### The Bias Engine is deliberately excluded from this sprint's seed — read this first

**This is the most consequential decision of this sprint.** The Master
Plan's own Sprint 2.1 text calls for seeding "all five engines' criteria
and weights." After extracting the actual source data from
`legacy/Trading Journal v2.0 Stable.xlsx` (methodology and full findings
below) and presenting it for review, the user approved seeding only
**Confidence, Quality, Execution, and Market Context** with real data.
`bias` is registered as a complete `engine_types` catalog row (migration
`0004`) but **intentionally receives zero `ScoringCriterion`/
`ScoringWeight` rows.**

**Why:** the Excel proves Bias does not use the same generic
weighted-criteria model the other four engines use, on three independent
counts:
1. **Bias's per-criterion scores are signed integers whose mapping from a
   selected category to a point value depends on the trading profile**
   (Day Trade vs. Swing) — e.g. the `DXY` criterion's "Strong Bullish"
   selection scores `-3` under a Day Trade profile but `-4` under Swing
   (`CHECKLIST` sheet, row 10's formula). `configuration.scoring_criteria
   .category_map` (`TRADEOS_DATABASE_DESIGN.md` §6.5) is a single,
   profile-independent JSONB column — it structurally cannot represent a
   mapping that varies by profile.
2. **Bias's final index divides by a fixed constant, not by the sum of
   active weights.** The real formula (`CHECKLIST` row 54) is
   `BIAS_INDEX = ROUND(GROSS_SCORE / 38 * 100)` for Day Trading/Scalping,
   or `/ 45 * 100` for Swing — `38`/`45` are hardcoded constants, not a
   sum of `scoring_weights.weight` rows. Domain Invariant INV-WEIGHT-01
   ("divide by the sum of active weights") does not describe this
   formula, and `configuration.scoring_weights` has no column to hold a
   per-profile normalizing constant at all.
3. **This directly contradicts `PROJECT_AUDIT.md` §3.2's own claim** that
   the Evaluation Engine is generic and "autonormalizado dividiendo por la
   suma de pesos activos, no una constante fija" (**"not a fixed
   constant"**) — true for Confidence/Quality/Execution/Market Context
   (all verified against their real formulas below), demonstrably false
   for Bias.

Forcing Bias's real behavior into `scoring_criteria`/`scoring_weights`/
`category_map` as they exist today was explicitly rejected rather than
worked around: any approximation (e.g., `weight = 1` per criterion, or
collapsing the two profile-dependent category maps into one) would compute
a **different score than the Excel actually produces**, and would have to
be redone regardless once Sprint 3.2 makes the real design decision. No
frozen document required modification to implement this exclusion — the
Domain Model, Database Design, Backend Blueprint, and API Specification
all continue to describe the generic five-engine model exactly as before;
only this sprint's own data-seeding scope was narrowed, and that scope
change lives here and in this module's own code comments
(`app/modules/configuration/domain/engine_type.py`,
`scripts/seed_configuration.py`'s module docstring), not in any `/docs`
file.

**Registered technical debt for Sprint 3.2** (which the Master Plan
already assigns "Bias's signed normalization" to): the Bias Engine's data
model is undecided and must be designed before Bias can be seeded or
computed. Candidate directions, evaluated but not decided here: extending
`category_map` with a profile dimension; a Bias-specific table separate
from `scoring_criteria`/`scoring_weights`; or modeling Bias's aggregation
entirely outside the generic Configuration schema. No design decision is
made by this sprint — only the fact that one is needed, and why.

### Excel data extraction — methodology and provenance

Since neither `PROJECT_AUDIT.md` §3.1/§6 (cited by the Master Plan) nor any
other frozen document contains the literal criteria names or numeric
weights, the real data was extracted directly from
`legacy/Trading Journal v2.0 Stable.xlsx` using `openpyxl`, installed only
into a throwaway virtualenv outside the project
(`AppData/.../scratchpad/xlsx_extract/.venv`) — **`openpyxl` is not a
dependency of this project**, not even a dev-dependency; `pyproject.toml`
is unchanged. The extraction was presented in full to the user (every
engine type, profile, criterion, weight, category-lookup table, and
inconsistency found) and approved before any seed code was written.

Sources read: the `⚙️ CONFIG` sheet's weight tables (rows 5-23), grade
thresholds (row 25, confirmed to apply only to Confidence and Quality —
Execution and Market Context have no letter grade in the Excel), 8
category-lookup tables (rows 31-76), and the Market Context Engine's two
normalized tables (rows 128-258: 30 criteria x 3 profiles = 90 weight
combinations, `Score_Normalizado`/`Contribución` columns discarded as
worked-example output, not configuration); the `📒 Trades` sheet's actual
`IF(...)`/`VLOOKUP(...)` formulas for the TRADE CONFIDENCE, TRADE QUALITY,
and EXECUTION SCORE columns (which additionally confirmed 5 of Quality's 6
criteria — Followed Plan, Valid Setup, Entered at Planned Level, Respected
Stop, Respected Risk Mgmt — are simple `Yes=100/No=0` binaries with no
separate lookup table in `⚙️ CONFIG`, resolved by reading the real formula
rather than guessing); and that sheet's data-validation dropdown lists,
which confirmed the exact category options in practice.

**Confidence/Quality/Execution weights are profile-independent in the
Excel** (a single global weight per criterion, not one per Day
Trading/Swing/Scalping). Since `scoring_weights.profile_code` is a
required column in the frozen schema, each of those weights is seeded
identically across all three profiles — a lossless, faithful translation
(the real weight never varies by profile; replicating one true value three
times changes nothing about what gets computed), not invented data.
Market Context's weights are genuinely per-profile in the Excel and are
seeded 1:1, unchanged.

### Added
- `app/modules/configuration/domain/` — `EngineType`, `ScoringProfile`,
  `ScoringCriterion`, `ScoringConfigurationVersion` (with `DRAFT`/
  `PUBLISHED`/`SUPERSEDED` status constants), `ScoringWeight` dataclasses
  (`TRADEOS_DOMAIN_MODEL.md` §8.4-8.6).
- `app/modules/configuration/infrastructure/models.py`, `repository.py` —
  typed `Mapped`/`mapped_column` models for all 5 tables
  (`TRADEOS_DATABASE_DESIGN.md` §6.3-6.7) and one repository per
  aggregate/table.
- `app/modules/configuration/application/` — 11 Use Cases:
  `ListEngineTypesUseCase`, `ListScoringProfilesUseCase`,
  `CreateScoringProfileUseCase`, `ListScoringCriteriaUseCase`,
  `CreateScoringCriterionUseCase`, `UpdateScoringCriterionUseCase`,
  `DeactivateScoringCriterionUseCase`,
  `ListScoringConfigurationVersionsUseCase`,
  `CreateDraftConfigurationVersionUseCase` (copies forward the
  currently-published version's weights, per §6.6's own "implementation
  convenience" framing), `UpdateDraftWeightsUseCase` (add-or-update,
  `409` off a non-draft version), `PublishScoringConfigurationVersionUseCase`
  (`TRADEOS_BACKEND_BLUEPRINT.md` §4.4 in full: validates every active
  weight's criterion is itself active, flips the target to `published` and
  the prior published version to `superseded` in the same transaction,
  publishes `ScoringConfigurationChanged` through the platform dispatcher
  — the first Use Case in this codebase to actually publish a Domain
  Event, Sprint 0.1's dispatcher having stood unused until now).
- `app/modules/configuration/presentation/schemas.py`, `router.py` — the
  full Configuration Module endpoint surface
  (`TRADEOS_API_SPECIFICATION.md` §6.6): engine-types, scoring-profiles,
  scoring-criteria, and versions — 11 endpoints, all behind
  `get_current_user_id` (§4.5-4.6: Configuration resources are global to
  the single user today, not yet per-user owned, but still sit behind the
  same bearer-token requirement as every other endpoint in this API).
- `alembic/versions/0004_create_configuration_schema.py` — the
  `configuration` schema, all 5 tables, the partial unique index on
  `engine_types.is_signed` (§6.3.1: at most one active signed engine,
  Domain Invariant DI-05), and a data seed for `engine_types` (5 rows,
  including `bias`) and `scoring_profiles` (3 rows) — reference data with
  no `user_id` attribution requirement, unlike the first
  `ScoringConfigurationVersion` (see below).
- `backend/scripts/seed_configuration.py` — an idempotent, manually-run
  script that seeds the real Confidence/Quality/Execution/Market Context
  criteria and weights and publishes the first `ScoringConfigurationVersion`,
  using the same Application-layer Use Cases the HTTP API uses (never raw
  SQL), per the Master Plan's own "Dependencies: Phase 1 (a `user_id` must
  exist to attribute the seed action)." Requires `--user-id`; re-running it
  is a no-op once a published version exists. Run and verified against
  both the persistent dev database and a freshly-migrated one (see
  Verification).
- `app/platform/errors.py` — added `NotFoundError` (404) and
  `UnprocessableEntityError` (422), generic cross-cutting error types
  needed by Configuration's Use Cases (e.g. `404` for an unknown
  criterion/version, `422` for a business-rule violation distinct from
  Pydantic's own shape-validation `422`s) — reusable by any future module,
  not Configuration-specific.
- `tests/configuration/` — 5 domain unit tests + 19 integration tests
  (engine types/profiles seeded correctly, `bias` is the one signed
  engine, authentication required, profile/criterion CRUD and their `409`/
  `422` failure cases, partial-update preserves untouched fields,
  deactivate, draft-only weight mutability, publishing a non-draft `409`s,
  publishing with an inactive-criterion-referencing weight `422`s, and the
  Master Plan's own named Exit Criteria test: publishing a second draft
  correctly supersedes the first, with exactly one `published` version
  provable at any time).

### Modified
- `alembic/env.py`, `tests/conftest.py` — import Configuration's models;
  create the `configuration` schema and seed the same `engine_types`/
  `scoring_profiles` reference rows the migration seeds (`Base.metadata
  .create_all` only creates tables, it does not run a migration's own data
  seed) — guarded by an existence check, not a bare insert, since
  `postgres_container` is session-scoped and this fixture runs once per
  test function against the same already-seeded database.
- `app/main.py` — registers `configuration_router`.

### Implementation notes (not architectural decisions)
- **N+1 avoided in `PublishScoringConfigurationVersionUseCase`:** the
  first version validated every active weight's criterion with one query
  per weight; changed to one `list_all()` call building an in-memory set,
  since a single version can carry dozens of weights (Market Context alone
  seeds 90). Found and fixed during this sprint's own pre-commit audit,
  before any regression test was needed.
- **`scripts/seed_configuration.py` reaches into Identity's
  `UserAccountRepository` directly** (to validate `--user-id` refers to a
  real user before seeding). This is a bounded, deliberate exception to
  `TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3's module-boundary rule: the rule
  governs *modules* importing each other's infrastructure layer; a
  standalone, manually-run operational script outside `app/modules/` is
  tooling, not a module, the same category as Alembic migrations already
  crossing schema boundaries at the DB level (e.g. `scoring_configuration
  _versions.created_by_user_id` already references `identity.user_accounts
  .id`). Flagged here for visibility rather than silently exercised.
- **`ScoringCriterion.id`/`EngineType.code`-prefixed criterion IDs**
  (`confidence.htf_alignment`, `market_context.htf_align`, etc.): the
  Excel independently uses "HTF Alignment" as a criterion name in *both*
  Confidence (category-mapped) and Market Context (numeric-range) — a
  literal `HTF_ALIGN` id, `TRADEOS_DATABASE_DESIGN.md` §2.4.1's own
  example, would collide between engines. Every seeded criterion id is
  namespaced `<engine_type_code>.<snake_case_name>` to guarantee
  uniqueness while staying human-legible, per `scoring_criteria.id`'s
  documented purpose (stable, human-assigned, INV-CRITERION-01).

### Verification performed
- `docker compose down -v && up -d` + `alembic upgrade head` from an empty
  database — `0001 → 0002 → 0003 → 0004` all applied cleanly in sequence;
  repeated twice (once against the persistent dev database, once against
  a freshly torn-down-and-recreated one) together with a full run of
  `scripts/seed_configuration.py` against each, confirming idempotency
  (a second run against the already-seeded dev database correctly printed
  "nothing to do" and created no duplicate rows).
- `pytest tests/` — **70 passed** (24 new: 5 domain + 19 integration; 46
  carried over from Sprints 0.1-1.2). No regressions.
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean (105 source files).
- Audit pass before commit: zero cross-module imports out of
  `app/modules/configuration/` (confirmed by direct grep — Configuration
  depends on nothing, exactly `TRADEOS_BACKEND_BLUEPRINT.md` §3.5's "the
  most upstream context"); the only pre-existing cross-module import
  anywhere in `app/modules/` remains Identity → Preferences' Sprint 1.2
  factory call; HTTP response shapes verified field-for-field against
  `TRADEOS_API_SPECIFICATION.md` §6.6 for all 11 endpoints; no dead code,
  unused imports, or TODO/FIXME/HACK markers found in any file added or
  modified this sprint.

### Deferred
- Catalogs (`CatalogEntry` CRUD, all five kinds) — Sprint 2.2, per the
  Master Plan's own split, despite sharing this sprint's `configuration`
  schema.
- The Bias Engine's data model, and therefore its `ScoringCriterion`/
  `ScoringWeight` seed data — Sprint 3.2 (see above; registered as
  explicit technical debt, not silently skipped).
- Configuration & Catalogs frontend (Scoring Versions page, Catalogs
  Management page) — Sprint 2.3.
- Any actual score computation (the Evaluation Engine reading this
  Configuration data) — Phase 3; this sprint only stores and serves
  criteria/weights/versions.

## Sprint 2.2 — Catalogs Backend

Phase 2 of the Implementation Master Plan: `CatalogEntry` CRUD and
deactivation for all five kinds (Setup, Session, Strategy, Entry Trigger,
Mistake Tag), seeded with the 37 real entries confirmed in
`PROJECT_AUDIT.md` §3.1. Catalogs is a second API surface exposed from the
same Configuration backend module (`TRADEOS_BACKEND_BLUEPRINT.md` §3.6),
not a new top-level module — no new cross-module dependency was
introduced.

### Documented contradiction: Domain Model vs. API Specification/Backend Blueprint on reactivation

`TRADEOS_DOMAIN_MODEL.md` §13.3 diagrams `CatalogEntry`'s lifecycle with a
`reactivate` transition back from `Inactive` to `Active`:

```
( Active ) ──deactivate──▶ ( Inactive, still referenceable by historical Trades )
    ▲                                │
    └──────────── reactivate ────────┘
```

Neither `TRADEOS_API_SPECIFICATION.md` §6.7 nor `TRADEOS_BACKEND_BLUEPRINT.md`
§4.8 name a `reactivate` endpoint or Use Case anywhere — both only ever
name `deactivate`. This is a real contradiction between what the Domain
Model's own state diagram claims is possible and what the interface
contract (API Specification) and Use Case catalog (Backend Blueprint)
actually expose.

**Resolution (approved by the user):** implement only what the API
Specification and Backend Blueprint define. `POST /catalogs/{id}/deactivate`
exists; no `reactivate` endpoint or Use Case was added. No frozen document
was modified to resolve this — per the project's standing rule, `/docs` is
never edited. The Domain Model's diagrammed reactivation capability is
treated as **documented future work**, pending a coordinated update across
the Domain Model, API Specification, and Implementation Master Plan
together (so the three documents describe the same lifecycle again) —
not a decision this sprint is authorized to make on its own.

### Added
- `app/modules/configuration/domain/catalog_entry.py` — `CatalogEntry`
  dataclass, `VALID_KINDS` (`setup`/`session`/`strategy`/`entry_trigger`/
  `mistake_tag`, `TRADEOS_DATABASE_DESIGN.md` §6.8's check constraint).
- `app/modules/configuration/application/` — `ListCatalogEntriesUseCase`,
  `CreateCatalogEntryUseCase` (`(kind, name)` uniqueness, valid-kind
  validation), `UpdateCatalogEntryUseCase` (renames only — `kind`,
  `is_active`, `id`, and both timestamps are outside this Use Case's
  signature entirely, not merely ignored at the API layer), and
  `DeactivateCatalogEntryUseCase` (Domain Invariant DI-10; publishes
  `CatalogEntryDeactivated` through the platform dispatcher — Create/
  Update publish nothing, per Open Question BE-3, exactly mirroring
  Sprint 2.1's `ScoringCriterion` Use Cases' event posture).
- `app/modules/configuration/presentation/catalog_schemas.py`,
  `catalogs_router.py` — the full Catalogs Module endpoint surface
  (`TRADEOS_API_SPECIFICATION.md` §6.7: `GET`/`POST /catalogs`,
  `PATCH`/`POST .../deactivate /catalogs/{id}`), mounted at `/catalogs`
  (not `/configuration/...`) from this same backend module, behind
  `get_current_user_id` like every other endpoint in this API.
  `UpdateCatalogEntryRequest` has no `kind`/`is_active` field at all, so
  there is no runtime check needed to reject them — they are structurally
  unreachable from this endpoint.
- `alembic/versions/0005_create_catalog_entries_table.py` — the
  `catalog_entries` table (`TRADEOS_DATABASE_DESIGN.md` §6.8: PK `id`
  UUID, `kind`/`name`/`is_active`/timestamps, unique `(kind, name)`, index
  on `kind`) and an idempotent seed of all 37 real entries via
  `INSERT ... ON CONFLICT (kind, name) DO NOTHING` — verified by directly
  re-running the insert against an already-seeded database and confirming
  zero rows changed and zero errors (see Verification).
- `tests/configuration/test_catalog_entry_domain.py`,
  `test_catalogs_flow.py` — 3 domain unit tests + 12 integration tests:
  authentication required, create defaults to active, invalid `kind`
  `422`s, duplicate `(kind, name)` `409`s (the Master Plan's own named
  Exit Criteria), the same name is allowed across different kinds, list
  filters by kind, rename via `PATCH`, `PATCH` cannot smuggle in `kind`/
  `is_active` changes, renaming into a collision `409`s, deactivate
  (including that it never hard-deletes — the entry remains listed, only
  `is_active` flips), `CatalogEntryDeactivated` durably logged to
  `platform.event_log`, and a dedicated test reproducing the exact
  37-entry real seed through the API/Use Case path independently of the
  migration, asserting all 37 are created active.

### Modified
- `app/modules/configuration/infrastructure/models.py`,
  `repository.py` — added `CatalogEntryModel` and `CatalogEntryRepository`
  to the existing files (matching how Sprint 2.1 grouped every
  Configuration model/repository together), rather than new files, since
  Catalogs is the same backend module, not a new one.
- `app/main.py` — registers `catalogs_router` alongside
  `configuration_router`.

### Implementation notes (not architectural decisions)
- **Seeded directly in the migration, no separate script** (unlike
  Sprint 2.1's `scripts/seed_configuration.py`): `catalog_entries` has no
  `created_by_user_id` column, and the Master Plan's Sprint 2.2 text names
  no Phase-1 user-attribution dependency the way Sprint 2.1's did —
  nothing requires an already-registered user to exist before this data
  can be seeded, so the same migration-level pattern already used for
  `engine_types`/`scoring_profiles` (Sprint 2.1) applies here for all 37
  rows.
- **Strategy names have the Excel's visual numbering prefix stripped**
  ("1. Daily Open" → "Daily Open") — approved as a data-cleanup decision;
  the numbering was a `⚙️ CONFIG` sheet ordering aid, never part of the
  business name itself.
- **Idempotency mechanism:** `INSERT ... ON CONFLICT (kind, name) DO
  NOTHING` rather than a plain `bulk_insert` (Sprint 2.1's
  `engine_types`/`scoring_profiles` seed, which is safe only because
  Alembic guarantees a given migration body runs at most once per
  database under normal operation) — the user explicitly asked for this
  migration specifically to tolerate being re-run, verified directly (see
  Verification).

### Verification performed
- `docker compose down -v && up -d` + `alembic upgrade head` from an empty
  database — `0001 → 0002 → 0003 → 0004 → 0005` all applied cleanly in
  sequence; `configuration.catalog_entries` confirmed at exactly 37 rows,
  5 kinds (`setup`=8, `session`=6, `strategy`=4, `entry_trigger`=3,
  `mistake_tag`=16), all `is_active = true`.
- **Idempotency directly verified**, not merely asserted: re-executing the
  seed's exact `INSERT ... ON CONFLICT` statement by hand against the
  already-seeded database returned `INSERT 0 0` (zero rows affected, zero
  errors) and the total row count remained 37.
- `pytest tests/` — **85 passed** (15 new: 3 domain + 12 integration; 70
  carried over from Sprints 0.1-2.1). No regressions.
- `ruff format --check` / `ruff check` — clean.
- `mypy app` — clean (112 source files).
- Audit pass before commit: zero cross-module imports out of
  `app/modules/configuration/` beyond what already existed after Sprint
  2.1 (confirmed by direct grep — Catalogs added no new dependency, since
  it lives inside the same module); the only cross-module import anywhere
  in `app/modules/` remains Identity → Preferences' Sprint 1.2 factory
  call; HTTP response shapes verified field-for-field against
  `TRADEOS_API_SPECIFICATION.md` §6.7 for all 4 endpoints; no N+1 queries
  (every Use Case issues at most one lookup query, no per-row loops); no
  dead code, unused imports, or TODO/FIXME/HACK markers found in any file
  added or modified this sprint.

### Deferred
- `reactivate` — see the documented contradiction above; pending a
  coordinated Domain Model + API Specification + Master Plan update, not
  decided unilaterally by this sprint.
- Validating a `Trade`'s referenced Setup/Session/Strategy/Entry Trigger
  actually exists and is active — Phase 4 (`Trade` does not exist yet).
- Normalizing `Trade.mistakes` from free text to a real `trade_mistakes`
  reference (`KDD-06`) — Phase 4, `TagMistake` (Sprint 4.3); this sprint
  only seeds the canonical `mistake_tag` taxonomy Configuration already
  owns (confirmed by `TRADEOS_DATABASE_DESIGN.md` §14, `DB-6, resolved`).
- Catalogs frontend (Catalogs Management page) — Sprint 2.3.
- Any metadata field beyond `kind`/`name`/`is_active` — `TRADEOS_DATABASE
  _DESIGN.md` §6.8 states that is the complete confirmed shape today.

## Sprint 2.3 — Configuration & Catalogs Frontend (Milestone M2)

Phase 2's final sprint: the Scoring Versions page (view/publish) and the
Catalogs Management page, "an admin-facing screen pair fully wired to
Sprints 2.1-2.2's endpoints" — both rendered as two tabs under the single,
pre-existing `/configuration` route and sidebar entry
(`TRADEOS_FRONTEND_BLUEPRINT.md` §4.1: "Configuration: Scoring &
Catalogs"; §4.2: "sub-views are tabs, not separate sidebar entries" — no
navigation or routing change was needed, both already matched this
sprint's target shape from Sprint 0.3).

### A missing backend endpoint, found and fixed before the frontend could proceed

**This is the most consequential finding of this sprint.** While building
the Scoring Versions page's version-detail panel (`TRADEOS_FRONTEND
_BLUEPRINT.md` §8.5: "DataTable (criteria + their weights for this
version)"), no endpoint existed to read a version's current weights —
Sprint 2.1 had only ever implemented `POST /configuration/versions/{id}
/weights` (add-or-update **one** weight, returning only that one row).
There was no way to answer "what weights does this draft already have"
from the API at all.

Per the user's explicit instruction not to invent new endpoints or touch
the backend this sprint, implementation paused and this gap was reported
before writing any more frontend code. **Approved resolution:** add the
missing `GET /configuration/versions/{id}/weights` endpoint as a scoped,
explicitly-documented correction to Sprint 2.1 — not silently bundled
into "frontend work," and not worked around with a degraded UI that could
never show a draft's existing weights.

- `app/modules/configuration/application/list_configuration_weights.py`
  — `ListConfigurationWeightsUseCase` (pure read, delegates to the
  already-existing `ScoringWeightRepository.list_by_version`, itself
  unchanged since Sprint 2.1 — this was a presentation/application-layer
  gap, not a data-layer one).
- `app/modules/configuration/presentation/router.py` — the new `GET`
  route, same auth/response-shape conventions as every other endpoint in
  this router.
- `tests/configuration/test_configuration_flow.py` — one new integration
  test: an empty list before any weight exists, then the real weight
  after one is added via the existing `POST`.
- No migration, no schema change — `scoring_weights` and its repository
  method already existed; only the missing read path was added.

### Added
- `frontend/src/components/Tabs.tsx` — Radix Tabs wrapper (new
  dependency `@radix-ui/react-tabs`, approved), the first real consumer
  of `TRADEOS_FRONTEND_BLUEPRINT.md` §4.2's "sub-views are tabs" pattern;
  Statistics (Overview/By Dimension/Rolling, later phase) will reuse it.
- `frontend/src/components/ConfirmDialog.tsx` — Radix AlertDialog
  wrapper (new dependency `@radix-ui/react-alert-dialog`, approved —
  `AlertDialog` specifically, not the generic `Dialog`, matching
  `TRADEOS_API_SPECIFICATION.md` §3.5's "irreversible in effect"
  framing of publishing). Used only for the Publish confirmation
  (§6.8) — Catalog deactivation has no confirmation step, matching the
  documented flow (§6.11) exactly.
- `frontend/src/components/DataTable.tsx` — the first DataTable in the
  project (`TRADEOS_FRONTEND_BLUEPRINT.md` §7). No pagination or
  virtualization (§16 confirms neither is needed at Configuration/
  Catalogs' data volume). Keyboard-accessible row selection: native
  `row` role preserved, `tabIndex`/`Enter`/`Space` handling and
  `aria-selected` added rather than overriding the row's semantic role
  (see Bugs below).
- `frontend/src/components/Badge.tsx` — status indicator, built only
  from the color tokens already in `tailwind.config.ts` (`accent`/
  `muted`/neutral-bordered) — no new Design System tokens added.
- `frontend/src/features/configuration/{types.ts,api.ts,catalogsApi.ts,
  schemas.ts}` — types mirrored field-for-field from the real backend
  schemas (verified directly against the committed `schemas.py`/
  `catalog_schemas.py`, not just the API Specification prose); Zod
  validation limits matching the backend's own `Field(...)` constraints
  exactly (`max_length=40/120`, `weight >= 0`).
- `frontend/src/features/configuration/components/ScoringVersionsTab.tsx`
  — versions list, create-draft form, inline version-detail expansion
  (approved: no Drawer, no nested route — one URL, `/configuration`,
  throughout), read-only criteria/profile reference joined into the
  weights table, weight add/update form (rendered only when
  `status === "draft"` — "blocked entirely, not just validated," per
  §5.5 — the form doesn't exist in the DOM for a published/superseded
  version, not merely disabled), and the Publish action behind
  `ConfirmDialog`.
- `frontend/src/features/configuration/components/CatalogsManagementTab.tsx`
  — one page filtered by `kind` (§5.7/§6.11, not five separate pages),
  add/rename/deactivate, active-state `Badge`.
- `frontend/e2e/configuration-and-catalogs.spec.ts` — cross-stack E2E
  (same real-backend prerequisite as `auth-and-preferences.spec.ts`):
  full draft-create → weight-add → publish flow; catalog entry add →
  deactivate; unauthenticated redirect. Every test uses a unique label/
  name — Configuration/Catalogs data is global, not per-user
  (`TRADEOS_API_SPECIFICATION.md` §4.6), so the shared dev database's
  real Sprint 2.1/2.2 seed (`v1.0`, 37 catalog entries) and prior test
  runs' leftover rows are always still present.
- `frontend/src/features/configuration/schemas.test.ts` — 11 Vitest unit
  tests for the Zod schemas above.

### Modified
- `frontend/src/features/configuration/pages/ConfigurationPage.tsx` —
  no longer `PlaceholderPage`; hosts the two tabs.
- `frontend/src/components/ErrorBanner.tsx` — added an
  `UNPROCESSABLE_ENTITY` entry to the shared `PRESENTATION` map (see
  Implementation notes) — a visual-only fix, the HTTP contract itself is
  unchanged.
- `frontend/package.json` — added `@radix-ui/react-tabs` and
  `@radix-ui/react-alert-dialog` only, both pre-approved (Sections 4-5
  of this sprint's analysis). No TanStack Table, no icon library, no
  virtualization library — all explicitly declined as unnecessary at
  this data volume.

### Bugs found and fixed (during this sprint's own implementation and pre-commit audit)
- **`DataTable`'s keyboard-accessibility fix broke row semantics.** To
  satisfy `jsx-a11y/click-events-have-key-events` for clickable rows, the
  first version set `role="button"` on the `<tr>` — which overrides a
  table row's implicit `row` role entirely. The E2E test caught this
  immediately: `getByRole("row", ...)` could no longer find a just-created
  version because its accessible role had become `button`. **Fix:** kept
  the native `row` role, added `tabIndex`, `Enter`/`Space` key handling,
  and `aria-selected` — keyboard-operable without erasing the table
  semantics screen readers rely on.
- **`ErrorBanner`'s `PRESENTATION` map had no entry for
  `UNPROCESSABLE_ENTITY`** — Sprint 2.1 introduced this 422 code (see
  that sprint's own CHANGELOG entry on `INVARIANT_VIOLATION` vs.
  `UNPROCESSABLE_ENTITY`) but the shared error banner, written in Sprint
  0.3 before any real business-rule 422 existed, only knew about
  `INVARIANT_VIOLATION`. Without this fix, a real Configuration/Catalogs
  422 (e.g., publishing with an inactive criterion) would have rendered
  the generic "Something unexpected happened" fallback instead of a
  correct message. Presented identically to `INVARIANT_VIOLATION` (§17:
  plain language, code hidden from the primary message).
- **The dev database's Configuration seed data (criteria/weights/the
  published `v1.0` version) was missing** when cross-stack E2E testing
  began — a leftover consequence of Sprint 2.2's own "migrations from a
  clean database" verification (`docker compose down -v`), after which
  `scripts/seed_configuration.py` was never re-run. Not a code defect;
  re-ran the existing, unmodified Sprint 2.1 script to restore it, and
  confirmed this is purely a local dev-environment state issue, never a
  step skipped in the actual, already-committed migration/seed sequence.

### Implementation notes (not architectural decisions)
- **Radix Select + React Hook Form:** the project's existing `Select`
  (Sprint 1.2, Radix-based) had no prior usage inside an RHF-managed
  form. Integrated via RHF's `Controller` (the documented pattern for
  controlled third-party inputs) rather than manual `setValue`/`watch`
  wiring, for both the weight editor's Criterion/Profile pickers and the
  catalog entry creation form's Kind picker.
- **`zod.coerce.number()` needs two form-value types.** The weight
  form's raw input (a string from the number `<input>`) differs from its
  coerced output (a number); `useForm` is typed against `z.input<...>`,
  the resolver/submit handler against `z.output<...>` — otherwise
  `tsc` rejects the mismatch between what RHF's `defaultValues` expects
  and what `zodResolver` produces after coercion.
- **`staleTime: 60_000` for every Configuration/Catalogs query** — a
  concrete number for `TRADEOS_FRONTEND_BLUEPRINT.md` §2.7's "safe to
  cache client-side for short periods," which names no exact duration.
  Documented here as an implementation default, the same posture as
  prior sprints' undocumented-numeric-value decisions (e.g., Sprint 1.1's
  token expiry).
- **`Idempotency-Key` intentionally not sent.** `TRADEOS_API_SPECIFICATION
  .md` §3.6 describes it generally for every resource-creating `POST`,
  but the real backend (Sprints 2.1-2.2) never implemented handling for
  it on any Configuration/Catalogs endpoint. Sending the header from the
  frontend without backend support would be dead weight — no actual
  double-submission protection — so it was deliberately omitted.
  **Registered as backend technical debt** for a future sprint, not
  implemented as a no-op here.

### Verification performed
- `pytest tests/` (backend) — **86 passed** (1 new: the added `GET`
  weights endpoint; 85 carried over from Sprints 0.1-2.2). No
  regressions.
- `ruff format --check` / `ruff check` / `mypy app` (backend) — clean
  (113 source files).
- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` (frontend) —
  clean.
- `pnpm test` (Vitest) — **25 passed** (11 new; 14 carried over).
- `pnpm build` — succeeded (436.27 kB JS / 11.03 kB CSS, gzip 137.00 kB
  / 2.77 kB).
- `pnpm test:e2e` (Playwright) — **7 passed** (3 new: full draft-create/
  weight/publish flow, catalog add/deactivate, unauthenticated redirect;
  4 carried over from Sprints 0.3/1.2), run against the real backend on
  a database confirmed to hold the actual Sprint 2.1/2.2 seed data.
- Audit pass before commit: no cross-feature imports (every
  `features/configuration/*` file imports only from shared `src/api`,
  `src/components`, or within its own feature folder); no N+1-shaped
  data fetching (a fixed, small number of queries regardless of list
  size — no per-row query loops); no dead code, unused imports, or
  TODO/FIXME/HACK markers in any file added or modified this sprint;
  every new shared component (`Tabs`, `ConfirmDialog`, `DataTable`,
  `Badge`) confirmed to have a real consumer; basic accessibility
  verified (native table semantics preserved, keyboard operability on
  interactive rows, Radix-provided ARIA roles/focus-trapping on Tabs and
  AlertDialog, `aria-label` on every Select).

### Milestone M2 — achieved
Per `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7: a default
`ScoringConfigurationVersion` is published and all five Catalog kinds
hold real, Excel-derived seed data — true at the backend level since
Sprint 2.2's own close. This sprint makes it independently, visually
demonstrable through the UI: the Scoring Versions tab shows `v1.0` as
`published`, and the Catalogs Management tab shows all five kinds
populated, exactly as `PROJECT_AUDIT.md` §3.1 confirmed.

### Deferred
- `Idempotency-Key` support on Configuration/Catalogs `POST` endpoints —
  registered backend technical debt (see Implementation notes above),
  not this sprint's scope.
- `ScoringCriterion`/`ScoringProfile` create/edit UI — approved
  out-of-scope decision; the Master Plan's own "(view/publish)" framing
  and `TRADEOS_FRONTEND_BLUEPRINT.md` §5.5's User Actions list both
  confirm criteria are reference-only on this page.
- Catalog entry `reactivate` — no endpoint exists (Sprint 2.2's own
  documented contradiction between the Domain Model's lifecycle diagram
  and the API Specification/Backend Blueprint); nothing to wire up.
- Any Trading/Evaluation/Statistics page — later phases.

## Sprint 3.1 — Confidence & Quality Engines

Phase 3's first sprint: the generic `EvaluationEngine` weighted-scoring
core, and its first two real instances — Confidence and Quality
(`TRADEOS_DOMAIN_MODEL.md` §12.1). Pure domain layer only: no
infrastructure, no database access, no HTTP endpoint, no wiring to
Configuration's real (persisted) data — all explicitly approved scope,
matching the Exit Criteria's own "unit-tested with zero infrastructure
dependencies."

### The Master Plan's cited "reference code" does not exist in this repository

`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`'s Sprint 3.1 objective says
"Confidence already has reference code," citing
`TRADEOS_SYSTEM_ARCHITECTURE.md` §15's Known Gap, which in turn refers to
a `tradeos-backend` reference implementation. That code is not present
anywhere in this repository — confirmed already during Sprint 2.1
planning (`legacy/` holds only the source Excel) and again here. Nothing
was "ported." Confidence and Quality were built fresh from the real
weights/category-maps Sprint 2.1 already extracted, verified, and seeded
— the same source of truth, not a substitute for it.

### The historical `round_half_up` defect, reproduced with real data before being fixed

No document describes the defect's actual mechanism — only that it
existed and was fixed in the (absent) reference implementation. Rather
than guessing, the real, already-computed values for the two actual trade
rows in `legacy/Trading Journal v2.0 Stable.xlsx` were extracted and
hand-verified against Sprint 2.1's real seeded weights: row 2's raw
Confidence weighted score is exactly `48.5` (`|21|×0.5 + 40×0.2 +
100×0.15 + 100×0.15`), and Excel's own `ROUND(48.5, 0)` produces `49`.
Python's built-in `round(48.5)` produces `48` — Python 3's `round()` uses
round-half-to-even ("banker's rounding"); Excel's `ROUND()` rounds half
away from zero. They silently disagree exactly on `.5` boundaries. This
is the real, reproduced historical defect, not a hypothetical one.

**Fix:** `app/modules/evaluation/domain/rounding.py`'s `round_half_up()`,
built on `decimal.Decimal` with `ROUND_HALF_UP` (stdlib, no new
dependency), converting through `Decimal(str(value))` rather than
`Decimal(value)` directly — the latter would import the float's raw
binary-representation artifacts (e.g. `1.005` is actually stored as
`~1.00499999999999989...`) into the rounding decision, silently
reintroducing a different, subtler version of the same class of bug.
Permanently regression-tested (`tests/evaluation/test_round_half_up.py`)
against both real rows, explicitly contrasted against Python's `round()`
on the same value.

### Added
- `app/shared_kernel/value_objects.py` — `Grade` (enum), `Score`
  (dataclass). The first real use of `shared_kernel`
  (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.2's "one deliberate exception" to
  modules communicating only through contracts) since Sprint 0.1 first
  scaffolded the empty package.
- `app/modules/evaluation/domain/evaluation_criterion.py`,
  `evaluation_weight.py` — `EvaluationCriterion`/`EvaluationWeight`,
  Evaluation's **own** input DTOs, deliberately not
  `configuration.domain.scoring_criterion.ScoringCriterion`/
  `scoring_weight.ScoringWeight` — importing those would violate
  `TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3 (Forbidden Dependencies: a module
  may never import another module's domain layer directly). The real
  translation from Configuration's persisted rows into this shape is
  Sprint 3.2's `PreviewEvaluation` Use Case's job (Application layer),
  not this sprint's.
- `app/modules/evaluation/domain/criterion_breakdown_row.py` —
  `CriterionBreakdownRow` (Domain Invariant DI-08: every Score must be
  explainable). Not a `shared_kernel` type — §3.2 does not name it there;
  it lives in Evaluation's own domain layer, mirroring (never importing)
  `trading.evaluation_snapshot_breakdowns`'s eventual shape.
- `app/modules/evaluation/domain/scoring_core.py` — the generic core
  (`PROJECT_AUDIT.md` §3.2: "una clase de cálculo... instanciada 5
  veces"): `normalize()` (category-map lookup, or linear min/max rescale
  to 0-100 when no `category_map` is set — implemented now per your
  approval, even though Confidence's only numeric criterion is already
  0-100 by construction, so Sprint 3.2's Market Context is the first real
  exercise of the non-identity path) and `compute_weighted_score()`
  (INV-WEIGHT-01: divides by the sum of *active* weights only; a missing
  answer is excluded from both sides of the division — "handled
  gracefully," `TRADEOS_BACKEND_BLUEPRINT.md` §4.1 — never an error).
  Carries no rounding, no grading, and no per-criterion value transform —
  those are each specific engine's own concern, kept out of the shared
  core deliberately so it stays reusable by Execution/Market Context/Bias
  in Sprint 3.2 without inherited assumptions that don't hold for them.
- `app/modules/evaluation/domain/grading.py` — `derive_grade()` and the
  real grade thresholds (A+≥95, A≥90, B≥80, C≥70, else D — the same
  values already extracted from and approved against the Excel's `⚙️
  CONFIG` sheet in Sprint 2.1), plus `finalize_score()` (round + grade),
  factored out specifically to avoid duplicating that tail between
  `confidence_engine.py` and `quality_engine.py`. Hardcoded domain
  constants, not configurable — no frozen document models grade
  thresholds as data.
- `app/modules/evaluation/domain/confidence_engine.py` — `score_confidence()`.
  The only Confidence-specific logic beyond calling the shared core: its
  `bias_index_at_entry` criterion is scored on the *absolute value* of
  the signed Bias Index (`ROUND(ABS(AF2)*W_CONF_BIAS + ..., 0)` in the
  real Excel formula) — applied here, immediately before calling
  `scoring_core`, never inside the generic core itself (a future signed
  engine like Bias must not inherit it).
- `app/modules/evaluation/domain/quality_engine.py` — `score_quality()`,
  net-new (no reference code covered it). Domain Invariant DI-03 /
  INV-QUALITY-01 (Quality independent of P&L) is enforced *structurally*
  — the function's signature has no parameter shaped like a financial
  outcome anywhere, not merely "unused today."
- `tests/evaluation/` — 21 tests total:
  - `test_round_half_up.py` (5): the real historical case, an explicit
    contrast against Python's `round()`, the second real row, a negative
    value, and `ndigits` support.
  - `test_confidence_engine.py` (6): both known real rows, the
    absolute-value rule, INV-WEIGHT-01 (deactivating a weight changes the
    denominator), graceful handling of a missing answer, and a profile
    with no matching weights.
  - `test_quality_engine.py` (6): both known real rows — row 2 is a
    **losing** trade (`result=SL`, `pnl=-1.05` in the real Excel row)
    with `TRADE QUALITY=85` (Grade B), the concrete proof of DI-03, not
    just an assertion of it — the structural DI-03 signature-inspection
    test, `respected_tp`'s `"N/A"`-scores-like-`"Yes"` rule, and
    INV-WEIGHT-01.

### Verification performed
- `pytest tests/` — **102 passed** (16 new; 86 carried over from Sprints
  0.1-2.3). No regressions.
- `ruff format` / `ruff check` / `mypy app` — clean (122 source files).
- Audit pass before commit: an AST-based scan (not just a text grep) of
  every file under `app/modules/evaluation/` confirmed zero imports from
  `configuration` or any other business module — the only cross-package
  import anywhere in Evaluation's new code is `app.shared_kernel
  .value_objects`, the one approved exception
  (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.2); no duplication between
  `confidence_engine.py` and `quality_engine.py` (both are thin callers
  of the shared `scoring_core`/`grading` modules); no dead code, unused
  imports, or TODO/FIXME/HACK markers in any file added this sprint.

## Sprint 3.2 — Execution, Market Context & Bias Engines; Evaluation Preview

Phase 3's second sprint: completes the `EvaluationEngine` with the
remaining three instances of the generic core — Execution, Market
Context, and Bias — assembles all five into one `EvaluationResult`
orchestrator, and wires the whole thing to real, persisted Configuration
data for the first time via `PreviewEvaluationUseCase` and
`POST /evaluation/preview` (`TRADEOS_API_SPECIFICATION.md` §6.5). Every
engine — Confidence, Quality, Execution, Market Context, Bias — is now a
thin caller of the exact same `scoring_core.compute_weighted_score`, with
zero engine-specific branching inside the shared core itself.

### Bias Engine — Camino A: the binding Product Bible text wins over the raw Excel

Sprint 2.1 documented that the real Excel's `BIAS_INDEX` formula
(`ROUND(GROSS_SCORE / 38 * 100)` for Day Trading/Scalping, `/45` for
Swing, plus a category-to-point mapping that itself changes by profile)
does not fit the generic weighted-average model the other four engines
use. You approved **Camino A**: build Bias on the exact same, unmodified
`scoring_core.compute_weighted_score` as every other engine, using signed
category-map values instead of introducing an architectural exception —
grounded in `TRADEOS_PRODUCT_BIBLE.md` §8.2, explicitly marked "the
single most important part of this document... binding on every future
technical document," which states the self-normalizing,
sum-of-active-weights aggregation applies to all five engines and
separates Bias from the rest only on the *sign* of its normalized values.
`scoring_core.py` needed **zero Bias-specific changes** — every real Bias
criterion in the Excel is categorical, never a raw numeric range, so
`normalize()`'s min/max rescale path (the one place a signed range could
have been mishandled — it unconditionally rescales to a positive 0-100
span) is never exercised by Bias. The real Excel's fixed-constant
divisor and profile-dependent category maps remain documented, known
technical debt (Sprint 2.1, reaffirmed here), not implemented. Domain
Invariant DI-05 (Bias never derives a Grade) is enforced structurally —
`score_bias` inlines its own finalization (`Score(round_half_up(...),
grade=None)`) rather than reusing `grading.finalize_score`, so it cannot
acquire a Grade by accident, matching `TRADEOS_DATABASE_DESIGN.md` §6.12
(no `bias_grade` column).

**No real Bias data (criteria, category maps, weights) was seeded this
sprint.** Per your explicit instruction, a separate data-proposal
document is being prepared for review before any Bias seed code is
written — the domain engine is complete and tested against synthetic
fixtures only (`bias.test_macro_signal`, `bias.test_trend_signal`,
deliberately never resembling real Excel criterion names).

### Discovered mid-sprint: Execution/Market Context grade thresholds have no Excel source

While wiring `execution_engine.py`/`market_context_engine.py` to reuse
`grading.finalize_score` (so their Scores carry a Grade, per
`TRADEOS_DATABASE_DESIGN.md` §6.12's `execution_grade`/
`market_context_grade` columns), found that this silently assumed the
same A+/A/B/C/D thresholds (95/90/80/70) Sprint 2.1 extracted and scoped
explicitly to Confidence/Quality only — the real Excel's `⚙️ CONFIG`
sheet (row 25) defines no grade thresholds for Execution or Market
Context at all (see Sprint 2.1's own CHANGELOG entry). Flagged to you
before proceeding rather than shipping the assumption silently. **Your
decision:** reuse Confidence/Quality's thresholds for both, as a
conscious architectural decision, not an Excel replication — every
non-signed engine (Confidence, Quality, Execution, Market Context) is
modeled uniformly as Score + Grade via the one shared `finalize_score`,
with no grade-less variant introduced for any two of them; Bias remains
the sole signed exception. Replaceable without an architecture change if
a future Product Bible/Excel revision defines engine-specific thresholds.
Documented in `grading.py`'s module docstring and each engine's own
docstring, plus `shared_kernel/value_objects.py`'s `Score.grade` comment
(updated — it previously, incorrectly, implied Execution/Market Context
were gradeless).

### `checklist_answers` source_field → criterion_id translation, confined to the Application layer

`POST /evaluation/preview`'s request body keys `checklist_answers` by a
criterion's `source_field` (API Specification line 190), but Sprint 3.1's
domain engines work exclusively with the stable `criterion_id`
(INV-CRITERION-01). Per your instruction, that translation happens
exactly once, inside `PreviewEvaluationUseCase` (Application layer) —
Sprint 3.1's already-shipped, already-tested domain layer is untouched.

**Corrected mid-sprint, while preparing the Bias data proposal (below):**
the translation was first built as a strict `dict[str, str]`
(`source_field -> criterion_id`), assuming one real checklist field
belongs to exactly one criterion. Re-extracting the real Excel's Bias
Engine section (`legacy/Trading Journal v2.0 Stable.xlsx`, CHECKLIST
rows 48-54) to draft that proposal showed this assumption is false: the
real `BIAS_INDEX` formula reads the exact same raw fields (`dxy`, `spy`,
`atr`, and ~32 others) that Confidence, Execution, and Market Context's
own criteria already read — one real answer legitimately feeds more than
one engine at once. Flagged to you before proceeding (this touches
already-approved Sprint 3.2 code, not just new Bias data); you approved
the fan-out fix. `criterion_ids_by_source_field` is now
`dict[str, list[str]]`, and every criterion referencing a given
`source_field` receives that answer, not just the last one found while
grouping. Application layer only — the domain layer is still untouched.
Regression-tested: `test_preview_evaluation_source_field_fans_out_to
_multiple_criteria` (two criteria, two different engines, one shared
`source_field`, one answer, both engines score correctly off it).

### Configuration cross-module factories, mirroring the Sprint 1.2 Preferences pattern

Four `build_*` factories added to Configuration's own Application layer
so `PreviewEvaluationUseCase` can read Configuration data without ever
importing its domain or infrastructure directly
(`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3, Forbidden Dependencies) —
`build_get_configuration_version_use_case` (backing a genuinely new
`GetConfigurationVersionUseCase`, since no endpoint previously needed a
single-version lookup), `build_list_scoring_criteria_use_case`,
`build_list_configuration_weights_use_case`,
`build_list_scoring_profiles_use_case`. Each constructs its Use Case with
a single `Repository(session)` argument, exactly matching
`build_create_default_preferences_use_case` (Sprint 1.2).

### N+1 avoidance

`PreviewEvaluationUseCase` performs exactly three reads regardless of how
many engines or criteria are involved: scoring profiles once (validating
`scoring_profile`), scoring criteria once, unfiltered (grouped by
`engine_type_code` locally in Python), and weights for the resolved
version once (matched to each criterion's engine via an
id → engine_type_code map built while grouping criteria) — never one
query per engine. A published version's own publish-time validation
(Sprint 2.1: every active weight must reference an active criterion) is
relied upon rather than re-filtering by `criterion.is_active` here.

### Added
- `app/modules/evaluation/domain/execution_engine.py`,
  `market_context_engine.py`, `bias_engine.py` — the third, fourth, and
  fifth instances of the generic core. Execution: four real Sprint 2.1
  category-mapped criteria, no engine-specific transform. Market Context:
  the first real exercise of `scoring_core.normalize()`'s min/max
  rescaling path (30 real numeric criteria, no `category_map`); DI-04
  (independent of Bias's direction) enforced structurally via signature
  inspection, exactly like DI-03 for Quality. Bias: see above.
- `app/modules/evaluation/domain/evaluation_result.py` — `EngineInput`
  (one engine's own criteria/weights pair), `EngineResult`
  (score+breakdown), `EvaluationResult` (all five `EngineResult`s),
  mirroring `TRADEOS_API_SPECIFICATION.md` §6.5's response shape exactly.
- `app/modules/evaluation/domain/evaluation_engine.py` — `evaluate()`,
  the orchestrator composing all five engines into one `EvaluationResult`.
  Zero infrastructure dependencies — every `EngineInput` is supplied by
  the caller.
- `app/modules/configuration/application/get_configuration_version.py` —
  `GetConfigurationVersionUseCase` (new) + its `build_*` factory.
- `build_*` factories added to `list_scoring_criteria.py`,
  `list_configuration_weights.py`, `list_scoring_profiles.py`.
- `app/modules/evaluation/application/preview_evaluation.py` —
  `PreviewEvaluationUseCase`: resolves the configuration version,
  validates `scoring_profile`, fetches criteria/weights once each, does
  the source_field → criterion_id translation, calls `evaluate()`. No
  persistence, no transaction, no event
  (`TRADEOS_BACKEND_BLUEPRINT.md` §4.5).
- `app/modules/evaluation/presentation/schemas.py`, `router.py` —
  `POST /evaluation/preview`. Response mirrors an `EvaluationSnapshot`
  exactly; `bias` carries no `grade` key at all (not even `null`),
  matching §6.5's documented shape. Wired into `app/main.py`.
- `tests/evaluation/` — 19 new tests: `test_execution_engine.py` (2, real
  Excel-verified rows, extracted via a new scratchpad script
  `07_extract_execution_score.py` against Sprint 2.1's isolated,
  non-dependency `openpyxl` venv), `test_market_context_engine.py` (3,
  including DI-04's structural test), `test_bias_engine.py` (7,
  synthetic fixtures only, DI-05/DI-08), `test_evaluation_engine.py` (2,
  orchestrator-level DI-05/DI-08 across all five engines at once),
  `test_preview_evaluation_flow.py` (6, integration — the first tests
  exercising Evaluation against a real database, full HTTP round-trip
  through the real FastAPI app; includes the source_field fan-out
  regression test added during the mid-sprint correction above).

### Verification performed
- `pytest` (full suite) — **122 passed** (20 new; 102 carried over).
- `ruff format` / `ruff check` / `mypy` — clean (mypy's only two findings
  are pre-existing, unrelated to this sprint: a Starlette typing mismatch
  in `test_correlation_id_middleware.py` and a missing `types-python-jose`
  stub package, both present before Sprint 3.2).
- No schema changes this sprint — no new Alembic migration; `git status`
  confirms zero touched files under `infrastructure/models.py` or
  `alembic/versions/`.
- Special audit (per your request): zero forbidden cross-module imports
  in either direction between `evaluation` and `configuration` (grep
  confirmed no `from app.modules.configuration.(domain|infrastructure)`
  in Evaluation, and no `from app.modules.evaluation` in Configuration);
  zero duplication of the weighted-scoring algorithm across all five
  engines (each is a thin wrapper around the one shared
  `compute_weighted_score`); `PreviewEvaluationUseCase` confirmed at
  exactly three DB reads regardless of engine/criterion count (see N+1
  avoidance above); this repository has no dedicated ADR directory —
  architectural decisions are tracked here, in this CHANGELOG, against
  the frozen canonical documents.

### Deferred
- Execution, Market Context, and Bias engines — Sprint 3.2, per the
  Master Plan's own split (Bias's signed normalization, DI-05, and Market
  Context's independence from Bias's direction, DI-04, are each that
  sprint's own named Exit Criteria).
- The full `EvaluationEngine.evaluate() -> EvaluationSnapshot` orchestrator
  producing all five scores together — only makes sense once all five
  engines exist (Sprint 3.2's "Deliverables: all five engines complete").
- Any wiring to real Configuration data (reading the published
  `ScoringConfigurationVersion` from the database and translating it into
  `EvaluationCriterion`/`EvaluationWeight`) — Sprint 3.2's
  `PreviewEvaluation` Use Case, at the Application layer.
- `POST /evaluation/preview` and any other HTTP surface — Sprint 3.2.
- Any persistence (`evaluation_snapshots`/`evaluation_snapshot_breakdowns`)
  — Trading owns those tables and does not exist yet (Phase 4).

## Sprint 3.2 (continued) — Bias Engine real data, following the approved proposal

`PROPUESTA_DATOS_BIAS_ENGINE.md` (session-scoped review document, not
committed) was reviewed and approved with six explicit decisions before
any seed code was written. This entry documents what was actually
implemented, plus two things discovered only while implementing it that
required stopping and getting a further decision.

### The six approved simplifications, as implemented

Extracted from `legacy/Trading Journal v2.0 Stable.xlsx`, CHECKLIST
sheet's "04 · BIAS ENGINE" section (`GROSS_SCORE`'s 35 real inputs,
`⚙️ CONFIG` confirming no real per-criterion weight table exists for
Bias) and the real `C5` "Operation Type" dropdown (`Day Trade
Long/Short, Swing Long/Short, Breakout Long/Short` — confirmed via the
CHECKLIST sheet's own data validation list, not `scoring_profile`).

1. **Axis collapse:** the real "No-Swing" branch (Day Trade + Breakout,
   either direction) → both `day_trading` and `scalping`; "Swing" → only
   `swing_trading`.
2. **Scalping has no real data** — inherits Day Trading's real numbers
   verbatim (mechanical consequence of #1).
3. **3 direction-dependent criteria** (`btc_dom`, `liq_4h`, `liq_24h`)
   use the real "trade is Long" branch as one profile-uniform
   `category_map` — `category_map` has no direction axis. Registered as
   technical debt for Phase 4 (Trading), revisitable once
   `Trade.direction` exists.
4. **`atr`** branches on `Breakout Long/Short` in the real Excel (an axis
   with no `scoring_profile` equivalent at all); the real "No-Breakout"
   branch is used uniformly across all 3 profiles.
5. **Equal weights** — `BIAS_WEIGHT = 1/35`, every criterion, every
   profile it applies to. The real Excel sums all 35 unweighted; this is
   the only reading that adds zero invented weighting.
6. **11 of the 35 real fields** (the ones whose real category-to-point
   mapping genuinely differs between "No-Swing" and "Swing") are seeded
   as **two criterion rows** each (e.g. `bias.dxy` / `bias.dxy_swing`),
   both sharing the real `source_field` (`dxy`) — `scoring_criteria
   .category_map` cannot vary by profile on a single row. Net effect: 35
   real fields become **46** `scoring_criteria` rows for Bias.
   `scripts/seed_configuration.py`'s `BIAS_CRITERIA` (28 fields reusing
   Market Context's real `source_field`s, 7 exclusive to Bias:
   `setup_type`, `ltf_confirmation`, `correlation`, `invalidation`,
   `risk_reward`, `entry_zone`, `emotional_state`).

Not reproduced (already-accepted technical debt, unrelated to the six
above): the real fixed 38/45 divisor — Bias divides by the sum of active
weights instead (`INV-WEIGHT-01`).

### Discovered mid-implementation #1: BIAS_SCALE_FACTOR

With `BIAS_WEIGHT=1/35` and the real category points (mostly -4..+4, a
few to -5), the weighted average naturally lands around -5..+5, not the
Excel UI's -100..+100 (reached there only via the excluded 38/45
divisor). Flagged before implementing further; you approved rescaling
the final result by an explicit, isolated constant —
`BIAS_SCALE_FACTOR = 20` in `bias_engine.py` only, applied after
`compute_weighted_score`, before `round_half_up`. Not in
`scoring_core.py`, not in Configuration's data or schema — a
display/comparability decision, easily replaced by changing this one
line if a future revision changes the Bias data's natural range.
`tests/evaluation/test_bias_engine.py`'s synthetic fixtures and
`tests/evaluation/test_evaluation_engine.py`'s orchestrator tests were
updated to pre-scale magnitude (real-data-like, roughly -5..+5) so their
existing expected outputs (-80/80/50/-50 etc.) still hold after scaling.

### Discovered mid-implementation #2: Market Context's numeric criteria couldn't accept the fan-out's real answer

Testing the fan-out against real seeded data (not synthetic fixtures)
surfaced that `market_context.dxy` (Sprint 2.1) was seeded as a numeric
criterion (`min_value=-4, max_value=4`, no `category_map`) — it expected
`checklist_answers["dxy"]` to already be a converted number, while
Bias's new `bias.dxy` expects the real category label (`"Strong
Bullish"`). Both share the real `source_field` `dxy` by design; no
single answer could satisfy both. Flagged before proceeding, since
fixing it either way touches either the just-approved Bias data or
already-shipped Sprint 2.1 data. **Your decision:** `checklist_answers`
represents only the user's real label, never an already-normalized
value — Market Context is corrected, Bias is not.

**Fix:** the 28 Market Context criteria overlapping Bias's real fields
were converted from numeric min/max to a **precalculated `category_map`**
— each value computed once, at seed-data-authoring time, as
`(raw_point − min) / (max − min) × 100`, using the exact real Excel point
and this table's own already-shipped min/max. `normalize()` now does a
direct category lookup instead of a rescale, but returns the identical
number it always has for that answer — **a data-representation
correction, not an Evaluation behavior change**: same scores, same
grades, same API contract, zero changes to `scoring_core.py` or the REST
contract. 11 of these 28 also needed the two-row split (#6 above, same
real Day/Swing divergence, same mechanism) — e.g.
`market_context.dxy` / `market_context.dxy_swing`, with each row's
weight simply moved (not recomputed) from the single per-field entry
already in `MARKET_CONTEXT_WEIGHTS` via a new
`_split_profile_varying_weights` helper — no new weight data written by
hand. `market_context.macro_events` and `market_context.confluence` (the
2 Market Context criteria Bias's `GROSS_SCORE` doesn't read) are
deliberately untouched, still numeric — explicitly out of this
correction's scope, a known remaining inconsistency.

**Regression-tested:** `tests/configuration/test_market_context_category
_map_regression.py` — for every one of the 39 converted criterion rows
and every real category label, calls the real `scoring_core.normalize()`
both ways (old: numeric criterion fed the real raw point; new:
categorical criterion fed the real label) and asserts identical output
(39 parametrized cases + 1 structural count check = 40 tests).

### Added
- `scripts/seed_configuration.py` — `BIAS_CRITERIA` (46 rows),
  `BIAS_WEIGHT`, `_seed_bias_criteria()`; `MARKET_CONTEXT_CRITERIA`
  extended with `category_map` (41 rows, up from 30),
  `MARKET_CONTEXT_PROFILE_VARYING_FIELDS`,
  `_split_profile_varying_weights()`. `seed()` now seeds and publishes
  Bias in the same run as every other engine — the "Bias intentionally
  excluded" module-docstring section from Sprint 2.1 is replaced with
  the full data-provenance writeup (six simplifications, both
  mid-implementation corrections).
- `app/modules/evaluation/domain/bias_engine.py` — `BIAS_SCALE_FACTOR`.
- `scripts/__init__.py` — added so `scripts` resolves as one consistent
  package to both pytest (tests now import `scripts.seed_configuration`
  directly, monkeypatching its `SessionLocal`) and mypy (previously
  ambiguous between `seed_configuration` and `scripts.seed_configuration`
  once a second import path existed).
- `tests/configuration/test_seed_bias_engine.py` — first automated
  coverage of `seed_configuration.py` at all (previously "run manually,
  verify by eye"): idempotency (`seed()` called twice, asserts exactly
  46 Bias criteria and exactly one published version), per-profile
  weight sums (`day_trading`/`swing_trading`/`scalping` each sum to
  1.0), and the fan-out proven against real seeded data (`dxy` reaching
  both `market_context.dxy` and `bias.dxy` from one real answer). Uses
  its own dedicated, function-scoped Postgres container rather than the
  suite's shared one — `seed()`'s "skip if already published" guard is a
  whole-database invariant that would otherwise silently no-op whenever
  this file ran after any other test that already published a version.
- `tests/configuration/test_market_context_category_map_regression.py`
  — see above.

### Verification performed
- `pytest` (full suite) — **164 passed** (42 new this round: 2 seed
  integration tests, 40 Market Context regression tests; 122 carried
  over). One unrelated, pre-existing flaky failure observed once
  (`test_jwt.py::test_tampered_signature_is_rejected`) and confirmed
  non-reproducing on re-run, in isolation and in the full suite twice —
  not a regression from this work.
- `ruff format` / `ruff check` / `mypy` — clean (mypy's two findings are
  the same pre-existing, unrelated ones noted earlier in this sprint).
- Special audit (per your request, re-verified after the Market Context
  correction): zero forbidden cross-module imports between `evaluation`
  and `configuration` (unchanged from earlier in this sprint); the
  fan-out (`source_field -> list[criterion_id]`) confirmed working for
  Market Context and Bias simultaneously against real data, not just
  synthetic fixtures; `PreviewEvaluationUseCase` still performs exactly
  the same 4 DB reads regardless of Bias/Market Context's larger row
  counts (list scoring profiles, get configuration version, list
  scoring criteria once unfiltered, list weights once per version) — no
  new N+1 introduced; the seed is idempotent (verified by an automated
  test, not just by eye); every profile's Bias weights sum to exactly
  1.0 (verified by an automated test).

## Sprint 3.3 — Evaluation Preview Frontend

Phase 3's frontend sprint, per `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`:
*"the live-updating Evaluation preview widget embedded in the
(not-yet-built) Trade Entry flow's design, buildable now against
`POST /evaluation/preview` alone... a standalone, testable preview
component."* Milestone M3's frontend half. No backend, schema, or REST
contract change — `POST /evaluation/preview`,
`GET /configuration/scoring-criteria`, and
`GET /configuration/scoring-profiles` were already complete (Sprint 2.1,
2.3, 3.2).

### Approved decisions, as implemented

- Hosted at the already-scaffolded `/evaluation` route (replacing its
  placeholder) — Trade Entry (Phase 4) doesn't exist yet to embed it in;
  `EvaluationPage` is a pure host with zero preview logic of its own.
  `EvaluationPreviewForm` takes no props, fetches its own reference data,
  and owns all of its own state — dropping it into Trade Entry's Pro mode
  later (`TRADEOS_FRONTEND_BLUEPRINT.md` §8.2's `NewTradeModal`) is a
  one-line change.
- Five `ScoreRing`s only (score + grade; Bias signed, no grade) — no
  per-criterion breakdown table. That is the Rule Explorer's job,
  explicitly deferred to Phase 4 (`TRADEOS_FRONTEND_BLUEPRINT.md` §5.4;
  Master Plan Phase 3 notes: the Rule Explorer "explains a *historical*
  Trade's score and needs real Trades to explain").
- Errors render inline inside the widget (a small message + the
  checklist stays fully interactive), never through the app-wide
  `ErrorBanner` — `TRADEOS_FRONTEND_BLUEPRINT.md` §10's Evaluation
  Preview row: *"Inline; a failed preview never blocks continuing to
  fill the form, since preview is advisory."*
- `ScoreRing` built as a genuinely shared component
  (`src/components/ScoreRing.tsx`, not `features/evaluation/`) — §7 names
  it reused later by Trade Detail and the Rule Explorer, neither built
  yet.
- Zero new dependencies. `@tanstack/react-query`, Radix (`Select`),
  `zod`/`react-hook-form` were all already in `package.json`. Debounce is
  a small, hand-written, framework-free utility (`debounce.ts`) rather
  than a new package — deliberately not a React hook, so its timing is
  unit-testable with Vitest's fake timers alone
  (`TRADEOS_TECHNICAL_STACK.md` §10 names Vitest for pure-logic tests; no
  DOM/component-rendering library is part of this stack, confirmed by
  `vite.config.ts`'s own Sprint 0.3 comment — component-level interaction
  testing lives in Playwright E2E instead, not a new unit-testing
  dependency).

### Race-condition safety (your validation requirement)

`useQuery`'s `queryKey` includes the full debounced `(profile, answers)`
state, so React Query treats each distinct answer-set as its own query
identity — a slow, superseded request can never overwrite state for a
*newer* key once the user has moved on. `placeholderData: keepPreviousData`
keeps the last good snapshot visible during the gap (no flash-to-empty),
which is also what makes an out-of-order/slow response harmless: only the
result matching the *current* queryKey is ever rendered. Confirmed by the
"rapid edits" E2E test (four fills in immediate succession, exactly one
backend call, final score matches the *last* value only).

### Discovered mid-implementation: a real backend race condition (not fixed — out of this sprint's scope)

Writing the E2E fixtures (each test publishes its own Configuration
version, since Configuration criteria have no creation UI — read-only by
design, `ScoringVersionsTab.tsx`) reproduced two genuine backend bugs when
publishes run concurrently:

1. A crashing `sqlalchemy.exc.MultipleResultsFound` in
   `GetConfigurationVersionUseCase.get_published()` when two rows end up
   `status='published'` simultaneously.
2. Silent data loss: whichever publish call's "supersede the previous
   version" step finishes last wins — the other call's freshly-added
   weight is orphaned from ever being evaluated, with no error raised at
   all.

Root cause: `PublishScoringConfigurationVersionUseCase`'s
read-then-write "find the currently published version, supersede it,
publish the new one" sequence is not atomic, and
`TRADEOS_DATABASE_DESIGN.md` §6.6 lists only `version_label` as a Unique
Constraint on `scoring_configuration_versions` — no partial unique index
on `status='published'`, unlike the equivalent, already-used pattern on
`evaluation_snapshots.trade_id WHERE is_current = true` (§6.12). This is a
genuine gap between the Database Design's own narrative invariant ("never
updated once published... the prior version's status transitions to
superseded") and what it actually specifies as enforced.

**Not fixed here** — squarely a backend/schema change, explicitly out of
this (frontend-only) sprint's approved scope. Worked around at the test
level only: `e2e/evaluation-preview.spec.ts` runs its own tests serially
(`test.describe.configure({ mode: "serial" })`), and passes reliably run
in isolation. Running the full E2E suite together can still flake because
`configuration-and-catalogs.spec.ts`'s own publish test runs concurrently
in a different Playwright worker — a pre-existing risk this sprint made
visible, not introduced by it. Registered as technical debt for a future
sprint to fix (a DB-level partial unique index plus either row-level
locking or a single atomic UPDATE in the Use Case are the two most direct
fixes).

### Added
- `frontend/src/components/ScoreRing.tsx` — shared score/grade
  visualization (§7); Bias renders signed with no grade badge at all
  (prop omitted, not `null`, so the two shapes are distinguished in the
  type system, not just at runtime).
- `frontend/src/features/evaluation/types.ts`, `api.ts` — own copies of
  the Configuration read shapes/wrappers this feature needs
  (`TRADEOS_FRONTEND_BLUEPRINT.md` §2.4 — no cross-feature imports).
- `frontend/src/features/evaluation/debounce.ts` — the framework-free
  debounce utility described above.
- `frontend/src/features/evaluation/components/ChecklistField.tsx` — one
  criterion, rendered from real Configuration data: a `Select` of the
  real category labels when `category_map` is set, a bounded number
  input otherwise.
- `frontend/src/features/evaluation/components/EvaluationPreviewForm.tsx`
  — the sprint's actual deliverable; also exports
  `groupActiveCriteriaByEngine`/`upsertChecklistAnswer`, pure functions
  covering the checklist-construction logic independent of rendering.
- `frontend/src/features/evaluation/pages/EvaluationPage.tsx` — rewritten
  from Sprint 0.3's placeholder into the demo host described above.
- Tests: `debounce.test.ts` (collapsing rapid calls, quiet-period
  re-firing, `cancel()`), `components/evaluationLogic.test.ts` (grouping,
  active-only filtering, answer upsert/removal, non-mutation) — 9 new
  Vitest tests. `e2e/evaluation-preview.spec.ts` — 4 Playwright tests
  covering exactly your validation checklist: debounce reduces calls to
  one, the checklist never becomes non-interactive (before, during, or
  after a failure), a transient failure recovers on the next edit, and an
  unauthenticated visitor is redirected.

### Verification performed
- `vitest run` — **34 passed** (9 new; 25 carried over).
- `eslint` / `prettier --check` / `tsc -b --noEmit` — clean.
- `vite build` — succeeds (441 KB / 138 KB gzipped, unchanged bundling
  approach).
- `playwright test e2e/evaluation-preview.spec.ts` — **4/4 passed**, run
  in isolation (see the discovered backend race condition above for why
  "in isolation" is the meaningful claim right now). The other 7
  pre-existing E2E tests (`auth-and-preferences`,
  `configuration-and-catalogs`, `error-banner`) still pass unaffected.
- Audit: `grep` confirms zero imports of `features/configuration/*` from
  `features/evaluation/*` in either direction; `EvaluationPreviewForm`
  takes no props and is rendered unchanged by `EvaluationPage`, confirming
  it is embeddable elsewhere without modification.

## Technical debt closed — Configuration publish race condition

Implements `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md` in full (reviewed
and approved before any code was written) — the concurrent-publish race
discovered and documented, not fixed, during Sprint 3.3. Backend-only; no
REST contract change, no new dependency, no frontend change.

### What shipped, exactly as approved in the ADR

1. **`alembic/versions/0006_scoring_configuration_publish_uniqueness.py`**
   — a partial unique index,
   `CREATE UNIQUE INDEX ix_scoring_configuration_versions_one_published ON
   configuration.scoring_configuration_versions ((true)) WHERE status =
   'published'`, the same idiom already specified for
   `evaluation_snapshots.trade_id WHERE is_current = true`
   (`TRADEOS_DATABASE_DESIGN.md` §6.12). Preceded by an idempotent data
   -repair step (keep the most-recently-`published_at` row, supersede any
   others) so `upgrade()` succeeds even against a database already
   corrupted by the race this migration closes — verified directly: ran
   against the real local dev database (which still had leftover
   corruption-turned-single-row state from Sprint 3.3's manual repair)
   and, separately, against a throwaway Postgres from a fully empty
   history (`alembic upgrade head` from `0001`), plus a full
   downgrade/upgrade cycle.
2. **`ScoringConfigurationVersionRepository.lock_for_publish()`** — a
   `pg_advisory_xact_lock`, not a `SELECT ... FOR UPDATE` on the
   currently-published row: that row's *identity* changes on every
   publish, so a lock tied to "whichever row currently matches
   `status='published'`" can go stale the instant a concurrent
   transaction changes which row that is (a transaction that blocked on
   the *old* published row isn't guaranteed to notice the *new* one once
   unblocked). An advisory lock keyed by a fixed constant has no such
   identity-shift problem — see the method's own docstring for the full
   reasoning, since this is exactly the kind of subtlety worth being able
   to re-derive later. Transaction-scoped (`_xact_lock`): released
   automatically on commit or rollback, no separate unlock call.
3. **`PublishScoringConfigurationVersionUseCase`** — acquires the lock
   before reading `get_published()`; supersedes the previously-published
   version *before* publishing the new one (reordered from the original
   code — see "bug found and fixed" below); catches `IntegrityError` from
   the explicit `session.flush()` and translates it to the same
   `ConflictError` (409) this Use Case already returns for "already
   published/superseded" — a new *reason* for an existing response shape,
   not a new one, so the REST contract is unchanged.
4. **`CreateDraftConfigurationVersionUseCase`** — takes the same lock
   before its own "copy forward the published version's weights" read,
   closing the ADR's second failure mode (a new draft silently seeded
   from a version that's already been, or is about to be, superseded).

### Bug found and fixed during implementation (not anticipated in the ADR)

The first version of the `PublishScoringConfigurationVersionUseCase` fix
published the new version *before* superseding the old one. Two
concurrent publishes, correctly serialized by the lock, still failed:
the *second* transaction's own flush hit
`ix_scoring_configuration_versions_one_published` immediately, because
for one statement mid-transaction *its own* newly-published row and the
old, not-yet-superseded row were simultaneously `published` — a
self-conflict, not a cross-transaction one. `ix_scoring_configuration
_versions_one_published` is a plain, non-deferrable constraint: Postgres
checks it immediately after each `UPDATE`, not batched at commit. Fixed
by superseding first, publishing second, so the published-row count only
ever moves 1 → 0 → 1 within a transaction, never 2. Caught immediately by
`test_concurrent_publishes_serialize_instead_of_both_committing` (below)
— exactly the kind of regression the ADR asked these tests to guard
against, working as intended on the first real bug it found.

### Added
- `tests/configuration/test_publish_concurrency.py` — three tests against
  a dedicated, isolated Postgres container (this suite asserts a *global*
  invariant, meaningless to check against a database other tests are
  concurrently publishing into), using real, independent database
  sessions run via `asyncio.gather` — not a sequential simulation:
  - `test_concurrent_publishes_serialize_instead_of_both_committing` —
    two drafts published at the same instant; asserts neither call
    crashes, exactly one row ends up `published`, and any exception
    surfaced is the documented `ConflictError`, never a raw
    `MultipleResultsFound` or `IntegrityError`.
  - `test_partial_unique_index_rejects_a_second_published_row_at_the_database_level`
    — a direct-SQL check independent of the application lock: even
    bypassing both Use Cases entirely, the database itself refuses a
    second `published` row.
  - `test_concurrent_create_draft_never_copies_a_torn_mix_of_two_versions`
    — the ADR's other failure mode: a new draft's copy-forward racing a
    concurrent publish; asserts the draft always ends up with exactly one
    real version's weights, never a torn mix of both and never neither.

### Verification performed
- `pytest` (full suite) — **167 passed** (3 new; 164 carried over). One
  unrelated, pre-existing flaky failure observed once
  (`test_jwt.py::test_tampered_signature_is_rejected`) and confirmed
  non-reproducing on immediate re-run, in isolation and in the full suite
  again — not a regression from this work (the same flake already noted
  in Sprint 3.2's and 3.3's own verification sections).
- `ruff format` / `ruff check` / `mypy` — clean (mypy's two findings are
  the same pre-existing, unrelated ones noted throughout this project).
- Migration verified three ways: applied to the real local dev database
  (already-corrupted-then-manually-repaired state from Sprint 3.3);
  applied to a fully empty database from `0001` through `0006`; a full
  `downgrade` → `upgrade` cycle confirmed the index is correctly dropped
  and recreated.
- Audit: zero `pyproject.toml` changes (no new dependency); zero new
  cross-module imports (`grep` confirms `configuration` still imports no
  other business module); no new N+1 — `lock_for_publish()` adds exactly
  one query per `execute()` call in each of the two affected Use Cases,
  not one per item; no REST contract change (`ConflictError` already
  existed as this Use Case's 409 response shape, only a new trigger for
  it).

### Confirmation
No `git push` was run at any point.

## Sprint 4.1 — Core Trade Registration

Phase 4 of the Implementation Master Plan, its first sprint: `POST /trades`
(`TRADEOS_API_SPECIFICATION.md` §6.4), the "single most important write in
the system" (§11.1) — INV-TRADE-01/02 validation, the synchronous
Trading → Evaluation call, persistence of `Trade` + `ChecklistSnapshot` +
`EvaluationSnapshot` (+ breakdown rows) in one transaction, and
`Idempotency-Key` support (§3.6). Out of scope, confirmed before
implementation began: `CloseTrade`, `AmendTrade`, `ReevaluateTrade`,
`DeleteTrade`, `TagMistake`/`trade_mistakes`, the Trading frontend, and
any change to Evaluation's or Configuration's own domain beyond two new
cross-module factories.

### Excel-derived business logic: the five computed properties

`PROPUESTA_FORMULAS_TRADE_COMPUTED_PROPERTIES.md` (repo root) — full
derivation, reviewed and approved before any domain code was written.
Extracted from `legacy/Trading Journal v2.0 Stable.xlsx`'s `Trades` sheet
via the same isolated `openpyxl` venv used in prior sprints (never a
project dependency). The real Excel has only 2 trade rows
(`last_row_with_data = 3`, both Long/SL) — both used as exact-match
regression cases; three further cases (Short, TP, and the `mfe_r == 0`
edge case) were hand-computed from the same confirmed formula, since the
real data contains no Short and no TP trade, each explicitly labeled as
such rather than presented as real. No hidden named ranges or lookup
tables, unlike the scoring engines — pure same-row arithmetic.

Three representation decisions, approved:
1. **`captured_pct`'s three Excel states collapse to two in the API.**
   The real formula (`=IF(OR(BB2="",BB2=0),"",IF(S2="TP",IFERROR(X2/BB2,""),"—"))`)
   produces a number only for TP trades, the literal text `"—"` for
   every other result, and blank when `mfe_r` is absent or zero. The API
   returns a number or `null` — `"—"` and blank both collapse to `null`,
   an editorial API-representation decision (matching how "not
   applicable" is already represented elsewhere in this API, e.g.
   `published_at: null`), not a business-logic change.
2. **`captured_pct` returns the raw ratio, never a scaled percentage.**
   The Excel column's own `number_format` is `"General"`, not `"0%"` — the
   stored/computed value is `0.8`, never `80.0`. The API returns that same
   raw ratio; formatting as a percentage is the frontend's job.
3. **`captured_pct` and `potential_left_r` do NOT share a "blank"
   condition, and this is deliberately preserved, not unified.**
   `captured_pct` treats `mfe_r == 0` as blank (`null`);
   `potential_left_r`'s real formula (`=IF(BB2="","",BB2-MAX(0,IF(X2="",0,X2)))`)
   only blanks on a genuinely *absent* `mfe_r`, and still computes a real
   number (`0.0`) when `mfe_r` is exactly zero. Verified with a
   hand-computed edge case (Case 5) and implemented as two independent
   `if` conditions in `Trade`, per explicit instruction not to simplify
   "for consistency."

### Resolved documentation gaps (stopped and asked before deciding, per standing instruction)

1. **`closed_at` has no input field, but INV-TRADE-02 requires one.**
   `TRADEOS_API_SPECIFICATION.md` §6.4 allows registering an
   already-closed Trade in the same `POST /trades` call (`result` +
   `exit_price` may be supplied at creation), and INV-TRADE-02's DB check
   constraint requires `closed_at IS NOT NULL` whenever `result != open`
   — but no document names `closed_at` as a request field. **Resolved:**
   `RegisterTradeUseCase` sets `closed_at = now()` server-side, at the
   moment the transaction is processed, whenever `result != open` AND
   `exit_price` is supplied — never accepted from the request, no new
   field added to the REST contract. If `result != open` but `exit_price`
   is missing, `closed_at` correctly stays `null` too, and
   `Trade.__post_init__`'s existing INV-TRADE-02 check rejects it as
   incomplete (422) for free — no extra Use Case logic needed. Explicitly
   scoped: this does **not** cover a future historical-import use case
   (a real past `closed_at`) — that would need its own explicit design
   (e.g. a dedicated import endpoint), not a reinterpretation of this one.
2. **`scoring_profile` is required by the Evaluation call this Use Case
   makes, but was never listed as a `POST /trades` request field.**
   `PreviewEvaluationUseCase.execute()` (which `RegisterTradeUseCase`
   reuses via the new `build_preview_evaluation_use_case` factory)
   requires `scoring_profile` to resolve which `ScoringWeight` rows
   apply — `POST /evaluation/preview` (§6.5) already lists it as
   required, but §6.4's `POST /trades` body never did, and no document
   names any other source for it (checked `UserPreferences` explicitly —
   no `default_scoring_profile` or equivalent exists). **Resolved:**
   `scoring_profile` is now a required field of `POST /trades`'s request
   body, propagated verbatim to `PreviewEvaluationUseCase` — never
   defaulted, never read from a preference, per explicit instruction:
   *"El perfil debe formar parte del contexto explícito con el que se
   registra cada trade."* This is a REST contract correction, not an
   addition: `POST /trades`'s own documented flow already implies an
   Evaluation call that cannot succeed without it.

### Idempotency-Key mechanism (`app/platform/idempotency.py`, cross-cutting Platform concern)

A new, generic `platform.idempotency_keys` table (migration `0008`), not
a `trades` column — reusable by any future `POST`-create endpoint.
Concurrency-safe by construction, per the explicit requirement to not
repeat the just-fixed Configuration publish race: `claim_idempotency_key`
attempts its `INSERT` inside a `session.begin_nested()` SAVEPOINT; the
`UNIQUE (user_id, idempotency_key)` index (never a "SELECT to check, then
INSERT" sequence) is what actually rejects a concurrent duplicate — the
SAVEPOINT only ensures a losing INSERT's `IntegrityError` unwinds cleanly
without poisoning the surrounding request transaction. The claim row, the
wrapped Use Case's own writes, and the later response UPDATE all commit
together, once, exactly like every other endpoint's transaction — so a
Use Case failure before that commit discards the claim automatically
(session close without commit = implicit rollback), with no separate
"release on failure" step needed. A losing concurrent request either
replays the winner's already-committed response (`StoredResponse`) or, if
the winner hasn't committed yet, gets `409 Conflict`.

### Other decisions

- **Catalog reference validation is literal, not kind-cross-validated.**
  `TRADEOS_BACKEND_BLUEPRINT.md` §4.1's precondition is "referenced
  Catalog entries (if any) exist and are active" — `RegisterTradeUseCase`
  checks exactly that for `strategy_id`/`setup_id`/`session_id`/
  `entry_trigger_id`, via Configuration's new `GetCatalogEntryUseCase`
  factory. It does **not** verify that, e.g., `strategy_id` actually
  references a `kind='strategy'` row — no frozen document asks for this,
  and adding it would be inventing a rule beyond the literal
  precondition. Noted here as a deliberate reading, not an oversight.
- **`mistake_ids`** (named in §6.4's request body) is not accepted by
  this sprint's `RegisterTradeRequest` — `TagMistake`/`trade_mistakes`
  belong to Sprint 4.3, per the Master Plan's own sprint boundary,
  confirmed explicitly in this sprint's approved out-of-scope list.

### A real bug found and fixed during implementation

Both `RegisterTradeUseCase` (Trade → ChecklistSnapshot/EvaluationSnapshot)
and `EvaluationSnapshotRepository.add()` (EvaluationSnapshot → its
breakdown rows) initially added parent and child rows to the session
without an intervening flush. This codebase declares no SQLAlchemy
`relationship()` between any of its mapped classes (plain FK columns
only, matching every prior module) — without one, the ORM's unit-of-work
has no dependency information to order INSERTs correctly across
*different* mapped classes on its own, and the flush inside
`session.commit()` attempted `INSERT INTO checklist_snapshots` before
`INSERT INTO trades`, tripping the FK constraint
(`ForeignKeyViolationError`). Caught immediately by
`test_register_trade_returns_full_trade_with_evaluation` on first run —
never reached the manual-testing stage. Fixed with an explicit
`await self._session.flush()` right after each parent `add()`, before its
children are added — the same explicit-flush idiom this codebase already
uses elsewhere for ordering-sensitive writes (e.g.
`PublishScoringConfigurationVersionUseCase`'s own `session.flush()`
before translating `IntegrityError`).

### Architecture, as implemented

- New `trading` module: `domain/{trade,checklist_snapshot,evaluation_snapshot}.py`,
  `application/register_trade.py`, `infrastructure/{models,repository}.py`,
  `presentation/{schemas,router}.py`.
- Two migrations: `0007_create_trading_schema` (4 tables — deliberately
  excludes `trade_mistakes`, owned by Sprint 4.3, same precedent as
  `catalog_entries` being its own migration separate from the rest of
  `configuration`) and `0008_create_platform_idempotency_keys`. Both
  applied and verified via `alembic upgrade head` from a fully empty
  database, plus a full `downgrade` → `upgrade` round-trip.
- `trading.evaluation_snapshots` gets its partial unique index
  (`ix_evaluation_snapshots_one_current_per_trade`, "exactly one current
  snapshot per Trade") from day one, applying the same idiom
  `scoring_configuration_versions` only got retroactively after a real
  bug (migration `0006`) — this time proactively, since the pattern was
  already known.
- Two new cross-module factories, following the established pattern
  (Preferences, Sprint 1.2; Configuration→Evaluation, Sprint 3.2):
  `Configuration.get_catalog_entry.build_get_catalog_entry_use_case`
  and `Evaluation.preview_evaluation.build_preview_evaluation_use_case`
  (the latter also now used by `POST /evaluation/preview` itself,
  replacing that endpoint's own inline four-factory wiring — a pure
  refactor, zero behavior change).
- `RegisterTradeUseCase` reads `EvaluationResult`'s attributes
  structurally (`.confidence.score.value`, `.confidence.breakdown`, ...)
  without importing `app.modules.evaluation.domain.*` — the same
  discipline `PreviewEvaluationUseCase` itself already uses when
  consuming Configuration's domain types.
- Trading's own `EvaluationSnapshot`/`EvaluationSnapshotBreakdown`
  domain shapes mirror — never import — Evaluation's
  `EvaluationResult`/`EngineResult`/`CriterionBreakdownRow`, exactly as
  those types' own docstrings already anticipated back in Sprint 3.2.
  Same for the presentation layer: Trading's `EvaluationSnapshotResponse`
  duplicates Evaluation's response shape rather than importing it — with
  one deliberate divergence: its `score` fields are `float | None`
  (matching `evaluation_snapshots`'s nullable columns), not Evaluation's
  own non-optional `float` (a preview always computes a score fresh; a
  persisted snapshot's nullable columns exist specifically so a future
  sixth engine doesn't require rewriting history).

### Added
- `backend/app/modules/trading/` — full module (domain, application,
  infrastructure, presentation) for `POST /trades`.
- `backend/app/platform/idempotency.py` — the claim/replay mechanism
  described above.
- `backend/alembic/versions/0007_create_trading_schema.py`,
  `0008_create_platform_idempotency_keys.py`.
- `backend/app/modules/configuration/application/get_catalog_entry.py`,
  `backend/app/modules/evaluation/application/preview_evaluation.py`
  (factory added) — the two new cross-module factories.
- Tests: `tests/trading/test_trade_domain.py` (16 tests — the five
  computed properties against the two real Excel rows plus three
  hand-computed cases, and INV-TRADE-01/02 validation);
  `tests/trading/test_register_trade_flow.py` (9 HTTP-level integration
  tests through the real FastAPI app: full response shape with nested
  evaluation, an open trade's null computed properties, INV-TRADE-01/02
  rejections, missing/inactive catalog reference rejections, an active
  catalog reference accepted, authentication required, and
  Idempotency-Key replay without duplicating the Trade);
  `tests/platform/test_idempotency_concurrency.py` (3 tests against a
  dedicated, isolated Postgres container, real concurrent sessions via
  `asyncio.gather`: concurrent claims for the same key never both
  succeed, sequential replay after completion, and the UNIQUE index
  rejects a direct duplicate insert at the database level).

### Verification performed
- `pytest` (full suite) — **195 passed** (28 new; 167 carried over).
- `ruff format --check` / `ruff check` / `mypy app` — clean (142 source
  files).
- Migrations verified against a dedicated, disposable Postgres container
  (never the shared dev database): full chain `0001` → `0008` from
  empty, plus a `downgrade` → `upgrade` round-trip for `0007`/`0008`.
- Audit: zero `pyproject.toml` changes (no new dependency); `grep`
  confirms zero imports of `evaluation.domain`/`evaluation.infrastructure`
  or `configuration.domain`/`configuration.infrastructure` from
  `trading/`; no TODO/FIXME left in any new file; catalog-reference
  validation is 4 fixed, bounded queries (not a loop over an unbounded
  collection, so not a real N+1); two pre-existing concurrency test
  fixtures (`test_publish_concurrency.py`, `test_seed_bias_engine.py`)
  needed a `CREATE SCHEMA trading` addition, since `Base.metadata` is
  shared process-wide and now includes Trading's tables — fixed as part
  of this sprint's own regression sweep, not deferred.

### Confirmation
No `git push` was run at any point.

## Sprint 4.2 — Amend, Close, Re-evaluate, Delete

Phase 4, second sprint: `AmendTrade`, `CloseTrade`, `ReevaluateTrade`,
`DeleteTrade` (soft) — `TRADEOS_BACKEND_BLUEPRINT.md` §4.2–4.3, 4.8;
`TRADEOS_API_SPECIFICATION.md` §6.4's `PATCH /trades/{id}`,
`POST /trades/{id}/close`, `POST /trades/{id}/reevaluate`,
`DELETE /trades/{id}`. No new migration, no new dependency — every
column these four actions need already exists from migration `0007`.

### Resolved documentation gap: `scoring_profile` on `ReevaluateTrade`

Same class of gap as Sprint 4.1's own `POST /trades` fix, surfacing again
here: `ReevaluateTradeUseCase` calls `PreviewEvaluationUseCase`, which
requires `scoring_profile` — but `scoring_profile` was deliberately never
persisted anywhere (not on `trades`, not on `evaluation_snapshots`, per
Sprint 4.1's own explicit decision), and API Specification §6.4 lists
only `configuration_version_id` in `reevaluate`'s request body. **Resolved
(approved):** `scoring_profile` is now a required field of
`POST /trades/{id}/reevaluate` too — propagated verbatim, never
persisted, never defaulted, never read from a preference. All three
calls into Evaluation across this codebase (`POST /evaluation/preview`,
`POST /trades`, `POST /trades/{id}/reevaluate`) now share the exact same
explicit input contract.

### Scope boundaries resolved by citation (no gap, no question needed)

- **`PATCH /trades/{id}` cannot transition `result`/`exit_price`/
  `closed_at`.** Two independent citations converge on this: the
  lifecycle diagram (`TRADEOS_DOMAIN_MODEL.md` §13.1) only ever draws
  `Open──amend──▶Open` and `Closed──amend──▶Closed`, never
  `Open──amend──▶Closed`; and API Specification §3.5 states the rule
  directly — *"`POST /trades/{id}/close` — not `PATCH /trades/{id}` with
  `result` in the body — because closing enforces... `TradeClosed`."*
  `AmendTradeRequest`'s schema simply has no such fields; sending them is
  silently ignored (Pydantic's default extra-field behavior), verified by
  a dedicated regression test.
- **`direction` is confirmed amendable** — Backend Blueprint §4.8's own
  example ("changing `direction` without changing `stop_loss`") uses it
  as the canonical case for why the *full* merged state is re-validated,
  not just the changed field.
- **`checklist_answers` is never amendable** — `ReevaluateTrade` (§4.3)
  explicitly reloads the existing `ChecklistSnapshot` "(unchanged)."
- **`DeleteTrade` is idempotent** (§3.4: "`DELETE`... Soft-delete...
  Idempotent: Yes") — deleting an already-deleted Trade is a successful
  no-op, never a 404, a deliberate narrow exception to every other Sprint
  4.2 action's own "soft-deleted behaves as not-found" rule.
- **`GET /trades` and `GET /trades/{id}` are confirmed out of scope** —
  the Master Plan's own Sprint 4.2 *Objectives* line names only the four
  write actions; confirmed explicitly rather than added for testing
  convenience. All integration tests verify state via direct database
  reads, exactly as Sprint 4.1's own tests already did.
- **`ReevaluateTrade`'s concurrency mechanism is `SELECT ... FOR UPDATE`
  on the Trade row, not a `pg_advisory_xact_lock`** — confirmed as the
  right choice specifically *because* it differs from Configuration's
  publish-lock precedent: "the currently published version" is a row
  whose *identity* changes on every publish (ruling out `FOR UPDATE`
  there), but "Trade X" is always the same, stable row — a plain row
  lock has no such staleness problem here.

### Two real bugs found and fixed during implementation

1. **`Decimal`/`float` mismatch on every Trade read back from the
   database.** `TradeModel`'s `Numeric` columns come back from asyncpg as
   `decimal.Decimal`, not `float` — Sprint 4.1 never noticed because
   nothing ever read a `Trade` back from the database (`RegisterTradeUseCase`
   only ever worked with its own freshly-constructed, all-`float` object).
   Sprint 4.2 is the first code to call `TradeRepository.get_by_id()`, and
   `AmendTradeUseCase` was the first to mix a DB-loaded `Decimal` field
   with a freshly-patched `float` field on the same object — `Trade`'s own
   computed properties (`r_multiple`, etc.) do raw Python arithmetic on
   `self.entry_price - self.stop_loss`, which raises `TypeError` the
   instant one operand is `Decimal` and the other `float`. Caught
   immediately by `test_amend_trade_updates_facts_and_recomputes_properties`
   on first run. Fixed by casting every `Numeric`-backed field to `float`
   explicitly in `_trade_to_domain()` and in
   `EvaluationSnapshotRepository.get_current_by_trade_id()` (the same
   class of bug, fixed proactively there too, before it could bite).
2. **Test-data bug, not an application bug** (documented for completeness,
   since it looked like a real failure at first): an early draft of the
   `reevaluate` regression test created a *second, independent* set of
   scoring criteria for the second configuration version, with different
   `source_field`s than the original `ChecklistSnapshot`'s answers — so
   the reused checklist answer never matched any criterion under the new
   version, and the assertion failed for an uninteresting reason. Fixed by
   reusing the *same* criteria (global, shared across every configuration
   version — only weights are per-version) across both versions in the
   test, editing only a criterion's `category_map` between the two calls.

### Architecture, as implemented

- `evaluation_snapshot_mapping.py` (new): `build_evaluation_snapshot()`,
  extracted from `RegisterTradeUseCase`'s own Sprint 4.1 inline logic once
  `ReevaluateTradeUseCase` needed the exact same construction — reused,
  not duplicated. Zero behavior change to `RegisterTradeUseCase`.
- `TradeRepository` gains `get_by_id`, `get_by_id_for_update` (`FOR
  UPDATE`), `update` (full overwrite of every mutable column — safe
  because `AmendTradeUseCase` already re-validates the complete proposed
  state before calling it). `ChecklistSnapshotRepository` gains
  `get_by_trade_id`. `EvaluationSnapshotRepository` gains
  `get_current_snapshot_id`, `mark_not_current` (flushes internally,
  called *before* the new snapshot is added — same self-conflict lesson
  as `PublishScoringConfigurationVersionUseCase`), and
  `get_current_by_trade_id` (full read with breakdowns, for `TradeResponse.
  evaluation` on `AmendTrade`'s/`CloseTrade`'s responses).
- Four new Use Cases (`amend_trade.py`, `close_trade.py`,
  `reevaluate_trade.py`, `delete_trade.py`), all reusing the same free
  validator functions (`validate_stop_placement`,
  `validate_close_requires_result_and_exit_price`) `Trade.__post_init__`
  itself already calls — amendment, closing, and registration can never
  silently diverge on what counts as a valid Trade state.
- Presentation: `PATCH /trades/{id}` and `POST /trades/{id}/close` both
  return the same `TradeResponse` (with `evaluation` nested), per
  §6.4's "the updated Trade." `POST /trades/{id}/reevaluate` returns only
  `EvaluationSnapshotResponse` — §6.4 says "the new Evaluation Snapshot,"
  not "the updated Trade," a deliberate difference, not an oversight.
  `DELETE /trades/{id}` returns `204 No Content`.
- No new cross-module factories needed — reuses
  `build_get_configuration_version_use_case` and
  `build_preview_evaluation_use_case`, both already built in Sprint 4.1.

### Added
- `backend/app/modules/trading/application/{amend_trade,close_trade,
  reevaluate_trade,delete_trade,evaluation_snapshot_mapping}.py`.
- Tests: `tests/trading/test_trade_lifecycle_flow.py` (16 HTTP-level
  integration tests: amend updates facts and recomputes properties, amend
  re-validates the full merged state against INV-TRADE-01, amend silently
  ignores `result`/`exit_price`, amend 404s for not-found/not-owned/
  unauthenticated; close succeeds, preserves existing `mfe_price`/
  `mae_price` when omitted, 409s if already closed, 422s if
  `exit_price` missing; reevaluate produces a new current snapshot and
  supersedes the old one — verified directly against the database — 422s
  against a draft version, 404s for a missing Trade; delete soft-deletes
  and is idempotent, a soft-deleted Trade 404s on amend, delete requires
  authentication); `tests/trading/test_reevaluate_concurrency.py` (1 test
  against a dedicated, isolated Postgres container, real concurrent
  sessions via `asyncio.gather`: two concurrent `reevaluate` calls for the
  same Trade never leave two or zero current `EvaluationSnapshot`s).

### Verification performed
- `pytest` (full suite) — **212 passed** (17 new; 195 carried over).
- `ruff format --check` / `ruff check` / `mypy app` — clean (147 source
  files).
- Migration chain `0001` → `0008` re-verified against a fresh, disposable
  Postgres container (no schema changed this sprint, but re-confirmed
  anyway).
- Audit: zero `pyproject.toml` changes; `grep` confirms zero imports of
  `evaluation.domain`/`evaluation.infrastructure` or
  `configuration.domain`/`configuration.infrastructure` from `trading/`;
  no TODO/FIXME in any new file; no N+1 (every new repository method is a
  single bounded query, `AmendTradeUseCase.AMENDABLE_FIELDS` guard is an
  in-memory set difference); two pre-existing concurrency test fixtures
  needed a `CREATE SCHEMA trading` addition after Sprint 4.1 (documented
  there) — none needed further changes this sprint.

### Confirmation
No `git push` was run at any point.

## Sprint 4.3 — Mistake Tagging

Phase 4, third sprint: `TagMistake` — `TRADEOS_BACKEND_BLUEPRINT.md`
§4.6; `TRADEOS_API_SPECIFICATION.md` §6.4's `POST /trades/{id}/mistakes`.
No new dependency, no new cross-module factory (reuses
`build_get_catalog_entry_use_case`, already built in Sprint 4.1).

### Scope, confirmed narrower than the full API surface

`TRADEOS_API_SPECIFICATION.md` §6.4 groups three endpoints under
"Mistakes on a Trade" (`GET`, `POST`, `DELETE`), but the Master Plan's
Sprint 4.3 *Objectives* line names only `TagMistake` — same "Master Plan
Objectives, not the documented API surface, define sprint scope"
reasoning already applied to `GET /trades` in Sprint 4.2. Confirmed
explicitly before implementation: only `POST /trades/{id}/mistakes`
ships this sprint; `GET /trades/{id}/mistakes` (list) and
`DELETE /trades/{id}/mistakes/{catalogEntryId}` (untag) wait for a sprint
that names them.

### Resolved by citation (no gap, no question needed)

- **KDD-06's "exception" for Mistakes is about the legacy Excel/free-text
  implementation, not this sprint's target.** `TRADEOS_DOMAIN_MODEL.md`
  DI-09 flags Mistakes as the one place a Trade might reference a Catalog
  entry by copied text instead of stable identity — but KDD-06 itself
  clarifies this is acknowledged *technical debt* in the legacy code, and
  that the **target** model (a proper `catalog_entry_id` reference,
  exactly what `TRADEOS_DATABASE_DESIGN.md` §6.14's `trade_mistakes`
  already specifies) is canonical. Implemented the identity-based target
  model, not the legacy free-text one.
- **No Open/Closed precondition on tagging.** §6.14's own text — "rows
  may be added or removed while the Trade is `Open`; once `Closed`...
  not blocked at the database level" — is explicitly registered as **Open
  Question DB-2** (§14, priority Low): *"Domain Model does not specify
  whether post-closure mistake tagging is a normal or a notable action."*
  Backend Blueprint §4.6 names no such precondition either. Left exactly
  as unresolved as the documents themselves — not invented here.
- **Duplicate tag → `409 Conflict`, via the composite primary key, never
  a "check then insert."** No document addresses a duplicate
  `(trade_id, catalog_entry_id)` tag attempt directly, so this follows
  the one directly comparable precedent already in this codebase —
  `CreateCatalogEntryUseCase`'s own `(kind, name)` duplicate handling —
  applying the same `IntegrityError` → `ConflictError` translation
  `PublishScoringConfigurationVersionUseCase` already uses, rather than a
  `SELECT`-first existence check (`ADR_CONFIGURATION_PUBLISH_RACE_
  CONDITION.md`'s own lesson).
- **No `Idempotency-Key`.** Not named for this endpoint by any document
  (unlike `POST /trades`, explicit in Sprint 4.1). The composite primary
  key already makes a duplicate request safe on its own; there is no
  "network retry silently double-logs a new aggregate root" risk here,
  since tagging isn't creating a new Trade.
- **`201` response shape reuses an existing pattern, not an invented
  one** (per explicit instruction this sprint): `POST /configuration/
  versions/{id}/weights` is this codebase's own closest "junction/
  association create" precedent, and it returns the full domain shape of
  the created row (`ScoringWeightResponse`). `trade_mistakes` has no
  surrogate `id` (composite primary key, §6.14), so the same pattern
  adapted to its actual columns is `{trade_id, catalog_entry_id,
  created_at}` — reusing the *pattern* (return the full created-row
  shape), not inventing a new one to match a table with a different key
  shape.

### Architecture, as implemented

- `trading.trade_mistakes` (migration `0009`) — deferred from migration
  `0007` (Sprint 4.1), same precedent as `catalog_entries` (0005) being
  its own migration separate from the rest of `configuration` (0004).
  Composite primary key `(trade_id, catalog_entry_id)`, no surrogate
  `id`, per §6.14 exactly.
- `TradeMistake` (new domain value object, no invariants of its own —
  `kind`/active-status validation happens in `TagMistakeUseCase` against
  Configuration's own `CatalogEntry`, read via the existing factory).
- `TagMistakeUseCase`: same 404 convention as every Sprint 4.2 write
  action (not found / not owned / soft-deleted all identical); `kind`
  compared against the literal string `"mistake_tag"` rather than
  importing Configuration's domain constant — same structural-literal
  precedent as `reevaluate_trade.py`'s own `PUBLISHED = "published"`.

### Added
- `backend/alembic/versions/0009_create_trade_mistakes.py`.
- `backend/app/modules/trading/domain/trade_mistake.py`,
  `application/tag_mistake.py`.
- `TradeMistakeModel`/`TradeMistakeRepository` in Trading's existing
  `infrastructure/{models,repository}.py`.
- `POST /trades/{id}/mistakes` in Trading's existing `presentation/
  {schemas,router}.py`.
- Tests: `tests/trading/test_tag_mistake_flow.py` (8 HTTP-level
  integration tests: successful tag, wrong `kind` rejected, inactive
  entry rejected, missing catalog entry rejected, duplicate tag returns
  `409`, Trade not found, Trade not owned, authentication required).

### Verification performed
- `pytest` (full suite) — **220 passed** (8 new; 212 carried over).
- `ruff format --check` / `ruff check` / `mypy app` — clean (149 source
  files).
- Migration chain `0001` → `0009` verified against a fresh, disposable
  Postgres container, plus a `downgrade` → `upgrade` round-trip for
  `0009` specifically.
- Audit: zero `pyproject.toml` changes; `grep` confirms zero imports of
  `evaluation.domain`/`evaluation.infrastructure` or
  `configuration.domain`/`configuration.infrastructure` from `trading/`;
  no TODO/FIXME in any new file; no N+1 (`TagMistakeUseCase` is two
  bounded reads plus one insert, regardless of any collection size).

### Confirmation
No `git push` was run at any point.

## Trading read endpoints — `GET /trades`, `GET /trades/{id}`, `GET /trades/{id}/evaluation`, `GET /trades/{id}/evaluation/history`

Closed ahead of Sprint 4.4 (Trading Frontend), by explicit approval, after an
Architecture Readiness Review surfaced a real gap in the Master Plan's own
dependency chain: Sprint 4.4's *Objectives* (Trades List, Trade Detail, the
Rule Explorer) are unbuildable without these four read endpoints, but no
sprint (4.1–4.3, all writes) ever claimed them, and Sprint 4.2 had
explicitly deferred `GET /trades`/`GET /trades/{id}` "to whichever sprint
first needs them" — this is that sprint. `TRADEOS_API_SPECIFICATION.md`
§6.4/§6.5/§7. Pure reads: no new migration, no change to any write action's
already-approved behavior or response contract.

### Response shapes — a new detail/summary split, not a contract break

- **`GET /trades/{id}` → `TradeDetailResponse`**: a new class, not an added
  field on `TradeResponse`. `TradeResponse` remains exactly `POST`/`PATCH`/
  `close`'s already-shipped contract (Sprints 4.1–4.2), untouched.
  `TradeDetailResponse` reuses that same shape and adds only
  `checklist_answers` — §7.4's own contrast with the list view ("list...
  omits... checklist_answers, which are fetched only via the
  single-resource endpoint") is the literal basis for putting it here and
  nowhere else.
- **`GET /trades` → `TradeSummaryResponse`**: every Trade fact
  `TradeResponse` exposes, minus `checklist_answers`, with a *lighter*
  nested evaluation shape (`EvaluationSnapshotSummaryResponse`: score+grade
  per engine, no breakdown rows) — §7.4, literally: "omits
  evaluation_snapshot_breakdowns and checklist_answers... to keep list
  responses cheap."
- **`GET /trades/{id}/evaluation/history` → `EvaluationHistoryEntryResponse`**:
  the existing `EvaluationSnapshotResponse` shape (full breakdown) plus
  `is_current`, `created_at`, `configuration_version_id` — §6.5, literally:
  "shaped like Section 6.5's single-snapshot response plus `is_current` and
  `created_at`," each entry "tagged with which `configuration_version_id`
  produced it."

### Pagination — real keyset, not offset dressed up as a cursor

`?cursor=` is documented as opaque to the client (§7.4 never specifies its
internal shape) — this implementation encodes it as base64 JSON of the
keyset tuple `(entered_at, id)` `TradeRepository.list_all` filters on,
decoded and validated in `presentation/pagination.py` (`422` on a corrupt
cursor). Deliberately never an offset internally: §7.4 explicitly rejects
offset pagination ("produces incorrect results under concurrent writes"),
so a page boundary is always a `WHERE` predicate on the last row's own sort
key. `has_more` is detected by fetching `limit + 1` rows and trimming the
extra one, avoiding a separate `COUNT` query. `entered_at` is the only sort
field implemented — the one literal example given (§7.1) and the
documented default (§7.2); no other sort field is named anywhere for
Trades, so none is invented.

### N+1 discipline

`GET /trades` needs the *current* `EvaluationSnapshot` of every Trade on
the page — `EvaluationSnapshotRepository.list_current_by_trade_ids()`
fetches all of them in one query (`trade_id IN (...)`), never one query per
row. `GET /trades/{id}/evaluation/history` fetches every snapshot for a
Trade in one query and every one of their breakdown rows in a second
(grouped in Python by `evaluation_snapshot_id`), never one breakdown query
per snapshot — same discipline `EvaluationSnapshotRepository.get_current_
by_trade_id()` already established in Sprint 4.1.

### Added
- `backend/app/modules/trading/application/{list_trades,get_trade,
  get_trade_evaluation,get_trade_evaluation_history}.py`.
- `backend/app/modules/trading/presentation/pagination.py`.
- `TradeRepository.list_all`, `EvaluationSnapshotRepository.
  {list_by_trade_id,list_current_by_trade_ids}` in Trading's existing
  `infrastructure/repository.py`.
- `TradeDetailResponse`, `TradeSummaryResponse`,
  `EvaluationSnapshotSummaryResponse`, `PaginatedTradesResponse`,
  `EvaluationHistoryEntryResponse` in Trading's existing `presentation/
  schemas.py`; the four new `GET` routes in `presentation/router.py`.
- Tests: `tests/trading/test_trade_reads_flow.py` (14 HTTP-level
  integration tests: empty list, summary shape/ordering, direction/result
  filtering, cursor pagination across two pages with no overlap, ownership
  scoping, authentication required, full detail with `checklist_answers`,
  404 for not-found/not-owned/soft-deleted, current-evaluation shape,
  evaluation history ordering with correct `is_current`/
  `configuration_version_id` per entry).

### Verification performed
- `pytest` (full suite) — **234 passed** (14 new; 220 carried over).
- `ruff format --check` / `ruff check` / `mypy app` — clean (154 source
  files).
- No new migration — every read is over columns migration `0007` already
  created.
- Audit: zero `pyproject.toml` changes; `grep` confirms zero imports of
  `evaluation.domain`/`evaluation.infrastructure` or
  `configuration.domain`/`configuration.infrastructure` from `trading/`;
  no TODO/FIXME in any new file; no N+1 (see above).

### Confirmation
No `git push` was run at any point.

## Frontend infrastructure prep — ahead of Sprint 4.4

Closed ahead of Sprint 4.4 (Trading Frontend), by explicit approval, as the
direct output of an Architecture Readiness Review performed before writing
any Trading Frontend code. The review's brief: identify decisions that are
"today still easy to fix but could become significant technical debt during
frontend development" — read-only, no implementation — across ten areas
(frontend architecture readiness, component-organization risk, React Query
audit, forms architecture, contract-drift risk, scalability, testing
strategy, performance, architectural consistency, prioritized risk list).
This entry covers the subset of that review's recommendations approved for
implementation now, before Sprint 4.4's actual pages: both items the review
flagged as blocking (critical), the two architecture decisions the review
asked to be ratified before Trade Entry exists, and three additional
infrastructure preparations approved the same sprint because they do not
require later redesign if implemented now. No Trading Frontend page (Trades
List, Trade Detail, Trade Entry, Rule Explorer) is part of this entry.

### Critical #1 — TanStack Table + TanStack Virtual, before the Trades List exists

The review's own scale test ("80+ pages, 150+ components") applied to a
Trades List backed by every Trade a user has ever logged made an unstyled
plain `<table>` a near-certain future rewrite. `TRADEOS_TECHNICAL_STACK.md`
§6.9 already mandates TanStack Table + TanStack Virtual for exactly this
case — installed now (`@tanstack/react-table@8.21.3`,
`@tanstack/react-virtual@3.14.8`) and built into a new, generic
`VirtualizedDataTable<T>` component (`frontend/src/components/
VirtualizedDataTable.tsx`). This is deliberately a **second** table
component, not a replacement for the existing `DataTable`: Configuration's
and Catalogs' tables stay on the simple one — Blueprint §16 itself says
virtualization is unneeded there, and migrating them would be premature
optimization outside this sprint's approved scope. Only the future Trades
List will use `VirtualizedDataTable`.

### Critical #2 — three-tier testing strategy, before Trade Entry exists

The review's testing-strategy audit found no component-level tier at all —
Vitest covered pure logic, Playwright covered nothing yet, and nothing
exercised a component's actual render/interaction behavior. Trade Entry
(Sprint 4.4) is exactly the kind of form-heavy, stateful component where
that gap would have been most expensive to close retroactively.
`@testing-library/react@16.3.2`, `@testing-library/jest-dom@7.0.0`, and
`@testing-library/user-event@14.6.1` are now installed, with `jsdom@30.0.0`
as the Vitest environment (`vite.config.ts`: `test.environment` changed
from `"node"` to `"jsdom"`, `test.setupFiles` now loads
`src/test-support/setupTests.ts`). The three tiers, and the explicit
boundary between them: **Unit** (Vitest, pure logic, `.test.ts`) → **Component**
(Vitest + `@testing-library/react`, jsdom, `.test.tsx`) → **E2E**
(Playwright, real browser). That boundary was tested empirically, not
assumed: `VirtualizedDataTable.test.tsx` tried asserting virtualized-row
rendering and click behavior at the Component tier first, and it failed —
jsdom has no real layout engine, so `@tanstack/react-virtual` computes zero
visible rows (`clientHeight`/`getBoundingClientRect` all report 0 in
jsdom). Faking a layout by stubbing those globally was tried and reverted:
it would only prove the stub works, not real behavior. The component test
now asserts only what jsdom can honestly verify (header rendering, empty
state); virtualized-row interaction is documented there as an E2E concern,
to be exercised once a real Trades List exists.

### Architecture decision #1 — Trade Entry module structure, ratified

The review proposed, and this entry ratifies as the official structure for
Sprint 4.4: `TradeEntryModal`, `SimpleForm`, `ProForm`, `ChecklistSection`,
`TradeEntryScorePreview`, `useTradeEntryForm`. No code for these exists
yet — this is a structural decision recorded now so Sprint 4.4 does not
redecide it mid-implementation.

### Architecture decision #2 — OpenAPI codegen deferral, recorded as technical debt

The review raised backend↔frontend contract drift risk (OpenAPI/DTO/TS/Zod
can silently diverge since every TS type is hand-mirrored from the Pydantic
schema). The decision, by explicit instruction: **do not** introduce
automatic OpenAPI type generation yet — manual TypeScript type mirroring
continues for now. This is recorded here specifically because the
instruction was to document it as technical debt for future review, not to
treat it as a closed question: as the API surface grows past Sprint 4.4
(more Trading endpoints, then Analytics, Reporting, Administration), the
manual-mirroring cost rises linearly with endpoint count while an
OpenAPI-codegen pipeline's setup cost is fixed — the trade-off should be
revisited once that crossover looks close, not deferred indefinitely by
default.

### Additional infrastructure prep approved this sprint

- **React Query key factories + a single `QueryClient`.** Every feature's
  query keys are now built by typed factory functions
  (`frontend/src/features/{evaluation,configuration}/queryKeys.ts`) instead
  of inline array literals — the review's own finding was that inline keys
  are how cache-key drift and stale `invalidateQueries` calls happen
  silently as the number of queries grows. `frontend/src/queryClient.ts`
  replaces the ad hoc `new QueryClient()` in `App.tsx` with one configured
  instance: `STABLE_DATA_STALE_TIME_MS = 60_000` for reference data that
  rarely changes (scoring criteria, profiles, configuration versions) and
  `LIVE_DATA_STALE_TIME_MS = 0` as the default for everything else, plus
  `retry: 1` (not TanStack Query's default of 3 — this codebase's own
  error envelope already distinguishes retryable from non-retryable
  failures; three silent retries before that surfaces was judged too
  slow to fail).
- **Scoring criteria/profile query deduplication.** `listScoringCriteria`/
  `listScoringProfiles` were implemented twice — once in
  `features/evaluation/api.ts`, once in `features/configuration/api.ts` —
  fetching the same Configuration data through two independently-typed,
  independently-cached paths. Both call sites now import from one new
  module, `frontend/src/shared/scoringReferenceData.ts`, which owns the
  canonical `ScoringProfile`/`ScoringCriterion` shapes and their query-key
  factory. This is a deliberate, narrow exception to "own DTOs per
  feature" — `src/shared/` is reserved for data genuinely needed
  identically by multiple features (mirroring the backend's own
  `shared_kernel` exception to per-module ownership), not a general escape
  hatch. `evaluation` and `configuration` were updated to import from it;
  `trading` will be its third consumer once Sprint 4.4 needs the same
  reference data.
- **`eslint-plugin-boundaries` enforcement of `TRADEOS_FRONTEND_BLUEPRINT.md`
  §2.4** ("cross-feature reuse goes through the shared component library,
  never through one feature importing another feature's internals
  directly"). Until now this was a comment-only convention — nothing
  failed a build if a future feature violated it, and the review's own
  scale test is exactly where that stops being reliable. `boundaries/
  elements` now classifies `src/features/*` (captured per-feature),
  `src/shared`, `src/components`, `src/api`, `src/auth`, `src/layout`;
  `boundaries/dependencies` denies by default and allows only same-feature,
  own-feature-to-shared-layer, and each shared layer's own legitimate
  dependencies (including `api → auth`, which the API client needs for
  reading the stored access token to attach `Authorization` — a real,
  already-shipped Sprint 1.2 dependency the policy set had to account for).
  **A real false negative was found and fixed while configuring this**:
  `eslint-plugin-boundaries` resolves import specifiers via
  `eslint-module-utils/resolve`, which had no `import/resolver` configured
  — every extension-less relative TS import (`"../auth/tokenStorage"`,
  effectively all of them) silently failed to resolve, so every
  dependency's target was classified `unknown` and the rule skipped it
  without ever reporting a violation. The rule looked configured and
  produced zero warnings, but provided zero actual protection. Diagnosed
  by enabling the plugin's own `ESLINT_PLUGIN_BOUNDARIES_DEBUG=1` output
  and inspecting a dependency's resolved `to` element directly. Fixed by
  installing `eslint-import-resolver-typescript@4.4.5` and pointing
  `settings["import/resolver"].typescript` at `tsconfig.app.json`. Verified
  with a repeatable smoke test (a temporary file importing across feature
  boundaries; confirmed `pnpm`/`eslint` now reports a real error; confirmed
  a clean baseline with the file removed) rather than trusting a clean
  exit code alone, since a clean exit code was exactly what the broken
  configuration also produced.
- `date-fns@4.4.0` and `lucide-react@1.27.0` installed ahead of need — the
  Trades List (date formatting) and the virtualized table (sort/expand
  icons) are their first consumers, in Sprint 4.4; neither is imported by
  any file yet.

### Verification performed
- `tsc --noEmit -p tsconfig.app.json` — clean.
- `eslint .` — clean, zero warnings (a first: every earlier boundaries
  configuration attempt produced deprecation or shape warnings even when
  it ran).
- `vitest run` — **36 passed** (7 test files), including the 2 new
  `VirtualizedDataTable` component tests.
- `vite build` — succeeds; 281 modules transformed.
- Smoke-tested `eslint-plugin-boundaries` twice: baseline clean, then a
  deliberately cross-feature-importing temporary file correctly reported
  as `boundaries/dependencies` error, then clean again after removing it.

### Confirmation
No `git push` was run at any point.

## Sprint 4.4 — Trading Frontend

Trades List, Trade Detail, Trade Entry (Simple and Pro), the Rule
Explorer, and Mistake-tagging UI — `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`
Sprint 4.4's objectives, Milestone M4 ("First Real Trade, End to End").
Built on every Sprint 4.1–4.4-prep decision already in place: the four
`GET` read endpoints, `POST /trades/{id}/mistakes`, `VirtualizedDataTable`,
the three-tier testing strategy, React Query key factories, and
`eslint-plugin-boundaries`.

### Resolved before writing any page: Simple vs. Pro default

Product Bible Open Question 4 / Master Plan OQ-2 ("Is 'Simple' or 'Pro'
Trade Entry the default daily workflow?") was still recorded as
unresolved in both source documents when this sprint began — re-read and
confirmed via an Explore pass before any code. Per your explicit
resolution: **Simple is the default** ("Simple (predeterminado)"); Pro
remains first-class but secondary in visual hierarchy ("Cambiar a Pro").
Both modes submit through the exact same `POST /trades` contract and one
shared `useTradeEntryForm` instance — only the capture experience
differs. Recorded in `09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §16
(OQ-2 retired from the blocking table, folded into the "explicitly not
included" explanation, mirroring the precedent already set there for
OQ-6) — the Product Bible itself stays frozen and unedited, per its own
"permanent foundation" status.

### A second genuine gap, found and resolved before Trade Detail: `GET /trades/{id}/mistakes`

Trade Detail's `MistakesCard` (`TRADEOS_FRONTEND_BLUEPRINT.md` §8.3)
needs to show `Badge × N` for mistakes already tagged to a trade — but
Sprint 4.3 shipped only `POST /trades/{id}/mistakes` (an explicit,
approved scope decision at the time: "no adelantar funcionalidades por
convenienca"). With no read endpoint, the card could not show what was
already tagged. Same category of gap as the four `GET` endpoints found
before this sprint started (an earlier sprint's deferral, now genuinely
needed) — stopped and asked before writing the card. Your resolution:
add `GET /trades/{id}/mistakes` now, same rigor as every other endpoint;
`DELETE /trades/{id}/mistakes/{catalogEntryId}` (untagging) stays out of
scope, since no Sprint 4.4 UI surface needs it yet.

- `TradeMistakeRepository.list_by_trade_id()` — one query, newest first.
- `ListTradeMistakesUseCase` — same 404 convention (not found / not
  owned / soft-deleted) as every other Trading read.
- `GET /trades/{id}/mistakes` reuses the existing `TradeMistakeResponse`
  shape (Sprint 4.3) — no new response contract.
- 5 new integration tests in the existing
  `tests/trading/test_tag_mistake_flow.py` (empty list, tagged entries
  returned newest-first, 404 not-found/not-owned, auth required).

### Frontend architecture: promoting checklist/preview/catalog logic to `src/shared/`

Building Trade Entry's Pro mode surfaced three more cases of the same
pattern the Architecture Readiness Review already established for
`scoringReferenceData.ts`: genuinely identical logic needed by two
features, which `eslint-plugin-boundaries` (shipped in the prior entry)
now correctly refuses to let one feature reach into another's internals
for. Each was promoted, not duplicated:

- **`ChecklistField`** (criterion → input/select rendering) moved
  `features/evaluation/components/` → `src/components/` — a generic,
  reusable UI component, not feature-specific.
- **`debounce`** and the checklist pure-logic pair
  (`groupActiveCriteriaByEngine`/`upsertChecklistAnswer`, plus the
  `ChecklistAnswers` type) moved to `src/shared/debounce.ts` and
  `src/shared/checklist.ts` — both were already unit-tested
  (`evaluationLogic.test.ts`); the tests moved with them
  (`src/shared/checklist.test.ts`, `src/shared/debounce.test.ts`).
- **`POST /evaluation/preview`** itself (request/response types, the
  `previewEvaluation()` call, its query-key factory) moved to
  `src/shared/evaluationPreview.ts`. This is deliberately **not** the
  same move as Trading's own persisted `EvaluationSnapshot` type in
  `trading/types.ts`, which still duplicates rather than imports — that
  one mirrors the backend's own "own DTOs per module" discipline
  (`schemas.py`'s docstring) because it's a genuinely different read
  (nullable, persisted, historical) over different data. The *preview*
  call is the exact same HTTP contract two features already needed
  unchanged, which is what `src/shared/` is for.
- **`GET /catalogs?kind=`** (the read only) moved to
  `src/shared/catalogEntries.ts` — Trade Entry's Pro mode
  (strategy/setup/session/entry-trigger pickers) and Mistake tagging's
  `CatalogPickerModal` both need it; Configuration's own catalog
  *writes* (`create`/`update`/`deactivate`) stayed in
  `features/configuration/catalogsApi.ts`, since only Trading needed the
  read. `CatalogsManagementTab.tsx`'s own inline `["catalogs", kindFilter]`
  query key was fixed to use the new `catalogEntryKeys` factory in the
  same pass — a pre-existing inline-key instance the Architecture
  Readiness Review's own rule (query keys always go through a factory)
  had not yet reached.

`features/evaluation/{api.ts,types.ts,queryKeys.ts}` were deleted
outright rather than left as thin re-export shims: `EvaluationPreviewForm`
was their only consumer, and after the above moves they held nothing
feature-specific left to own.

One new shared, generic component: **`src/components/Modal.tsx`**
(Radix Dialog, controlled `open`/`onOpenChange`) — `ConfirmDialog`
(Radix AlertDialog) is reserved for irreversible-action confirmations
per its own docstring; New Trade, Amend, Close, Re-evaluate, and the
Mistake-tag picker all need arbitrary form content plus a mutation's
`onSuccess` closing the dialog programmatically, which an uncontrolled
`Trigger`-only dialog can't do. `Tabs` (`src/components/Tabs.tsx`) grew
optional `value`/`onValueChange` props for the same reason — every
earlier consumer (Configuration) stays uncontrolled via `defaultValue`,
unaffected.

### Trade Entry — Simple and Pro, one shared form

`useTradeEntryForm` owns one `react-hook-form` instance (`FormProvider`)
so toggling Simple ↔ Pro never drops already-entered values, plus
`checklist_answers` state (not a registered field — a dynamic
per-criterion map, the same pattern `EvaluationPreviewForm` established).
One Zod schema (`tradeEntrySchema`) validates both modes — Simple
registers only the required subset (`market`, `direction`, `entry_price`,
`stop_loss`, `scoring_profile`); Pro registers every optional field plus
the checklist. `entryStopSideRefine` mirrors INV-TRADE-01 client-side
(`TRADEOS_FRONTEND_BLUEPRINT.md` §10: "a fast-feedback client check,
never the sole gate") — reused by `amendTradeSchema` too, conditionally,
only when a proposed amendment's direction/entry_price/stop_loss are all
present. `TradeEntryScorePreview` (Pro mode's live `POST
/evaluation/preview` binding, §6.3) and `ChecklistSection` both reuse the
shared debounce/checklist/preview modules unchanged.

### Trades List — the first real consumer of `VirtualizedDataTable`

Cursor pagination (`TRADEOS_API_SPECIFICATION.md` §7.4) modeled as
`useInfiniteQuery`, not manual cursor-state juggling — "Load more"
appends a page's rows to the already-virtualized list, matching the
opaque, forward-only cursor contract. Filters exactly match `GET
/trades`'s own filter set (direction, result, date range, strategy/setup/
session) — `FilterBar` invents nothing beyond it. This is the first time
`VirtualizedDataTable` renders real, variable-count data — E2E-verified
(below) against a real browser's real layout engine, closing the loop the
infra-prep entry above left open ("virtualized-row rendering/interaction
… deferred to E2E once Trades List exists").

### Trade Detail, Rule Explorer, Mistake tagging

`ActionBar` offers Close only while `result === "open"` (§5.3: "Close if
still Open"). `AmendTradeModal` submits the *entire* proposed state, not
a diff — `PATCH /trades/{id}` re-validates the full state, and the
Blueprint's own Forms table is explicit the frontend must not validate
only the changed field. `ReevaluateModal` carries `scoring_profile`
(`ReevaluateTradeRequest` requires it) but not `configuration_version_id`
— no document names that as a UI field, and the API defaults it to the
currently published version. `RuleExplorerPage`'s History tab: selecting
a row expands the same `ScorePanel × 5` layout used for the current
snapshot, per §5.4's own component tree. `JournalEntriesCard` is an
explicit placeholder — the Journal module (Phase 5) doesn't exist yet, so
there is no endpoint to read from; the card says so rather than silently
omitting the section the Blueprint's tree calls for.

### Testing — all three tiers, for real this time

- **Unit**: `trading/schemas.test.ts` — INV-TRADE-01 both directions,
  INV-TRADE-02 structural enforcement, amend's conditional refine.
- **Component**: `TradeSummaryCard.test.tsx`, `ScorePanel.test.tsx` — pure
  prop-driven components, no network, no layout dependency (the
  documented component-tier boundary from the infra-prep entry).
- **E2E** (`e2e/trading.spec.ts`) — run against the **real stack**: local
  Postgres (`docker compose up postgres`), the real FastAPI backend
  (`uvicorn`), and Playwright's real Chromium, not a simulation. Three
  tests: the full Milestone M4 golden path (create via Simple mode → tag
  a mistake → close → re-evaluate → Rule Explorer, current and history
  tabs), Trades List rendering a created trade and navigating to its
  detail on click (the real `VirtualizedDataTable` row-click interaction
  jsdom cannot honestly verify), and the unauthenticated-redirect guard.
  One real bug was caught and fixed during this run — not in the app: a
  test fixture's market string (`E2E-List-${Date.now()}`) exceeded the
  real 20-character backend limit, correctly triggering a `422` the test
  hadn't accounted for. The full pre-existing E2E suite (12 further
  tests across 4 files) was re-run alongside the new spec to confirm no
  regression; `evaluation-preview.spec.ts` intermittently fails when run
  concurrently with other files, reproduced here too — but this is the
  already-documented, pre-existing Configuration-publish race condition
  that file's own docstring names as known technical debt, confirmed
  unrelated to this sprint by re-running it in isolation (passes
  cleanly, 4/4).

### Added
- Backend: `backend/app/modules/trading/application/list_trade_mistakes.py`;
  `TradeMistakeRepository.list_by_trade_id()`; `GET /trades/{id}/mistakes`
  route; 5 new tests in `tests/trading/test_tag_mistake_flow.py`.
- Frontend shared: `src/shared/{checklist,debounce,evaluationPreview,
  catalogEntries}.ts` (+ `checklist.test.ts`, `debounce.test.ts`);
  `src/components/{Modal,ChecklistField}.tsx`.
- Frontend Trading feature: `src/features/trading/{types,api,queryKeys,
  schemas}.ts` (+ `schemas.test.ts`); `hooks/useTradeEntryForm.ts`;
  `pages/{TradesListPage,TradeDetailPage,RuleExplorerPage}.tsx`;
  `components/{FilterBar,TradeEntryModal,SimpleForm,ProForm,
  ChecklistSection,TradeEntryScorePreview,TradeSummaryCard,
  EvaluationSummaryCard,MistakesCard,CatalogPickerModal,ActionBar,
  AmendTradeModal,CloseTradeModal,ReevaluateModal,ScorePanel}.tsx`
  (+ `TradeSummaryCard.test.tsx`, `ScorePanel.test.tsx`).
- `e2e/trading.spec.ts` (3 tests).
- New routes: `/trades/:tradeId`, `/trades/:tradeId/evaluation`
  (`src/router.tsx`).
- `@radix-ui/react-dialog` dependency (for `Modal`).

### Verification performed
- Backend: `pytest` — **239 passed**; `ruff format --check` / `ruff
  check` / `mypy app` — clean (156 source files).
- Frontend: `tsc --noEmit` — clean; `eslint .` — clean, zero warnings,
  zero `boundaries/dependencies` violations; `vitest run` — **54
  passed** (10 test files); `vite build` — succeeds (311 modules).
- E2E: `playwright test` — **14 passed, 1 pre-existing documented flake**
  (unrelated to this sprint, confirmed via isolated re-run) across the
  full suite including the new `trading.spec.ts`.
- Audit: `grep` confirms zero TODO/FIXME in any new file; zero direct
  imports of `evaluation.domain`/`evaluation.infrastructure` or
  `configuration.domain`/`configuration.infrastructure` from `trading/`
  on the backend; the local dev stack (Postgres container, `uvicorn`
  process) spun up only for this verification was torn down afterward.

### Confirmation
No `git push` was run at any point.

## Sprint 5.1 — Journal Backend + Frontend

`CreateJournalEntry`/`UpdateJournalEntry`/`DeleteJournalEntry`; Journal
List/Detail pages; `JournalEntriesCard` on Trade Detail —
`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Sprint 5.1, Milestone M5
("Journal entries — trade-scoped and period-scoped — function against
real Trade data"). Pre-analysis re-read `TRADEOS_DOMAIN_MODEL.md` §8.10,
`TRADEOS_DATABASE_DESIGN.md` §6.17, `TRADEOS_BACKEND_BLUEPRINT.md`
§3.10/§4.7-4.8/§20, `TRADEOS_API_SPECIFICATION.md` §6.11, and
`TRADEOS_FRONTEND_BLUEPRINT.md` §5.3/§5.7/§6.10/§8.3/§10-11 — no genuine
business-decision gap was found; every apparent ambiguity resolved by an
already-established codebase precedent (below), never invented.

### A single unified `/journal-entries` resource

`TRADEOS_API_SPECIFICATION.md` §6.11 is explicit: one resource,
`POST/GET /journal-entries`, `GET/PATCH/DELETE /journal-entries/{id}` —
never nested under `/trades/{id}/journal`. Trade-scoped vs. period-scoped
is disambiguated purely by which fields are present in the request body,
matching `journal.journal_entries`' own exactly-one-of-(`trade_id`)-or-
(`period_start`+`period_end`) check constraint (`TRADEOS_DATABASE_DESIGN.md`
§6.17) — the only instance of a mutual-exclusivity-between-two-nullable-
FKs pattern anywhere in the schema; every other cardinality rule in this
codebase is a single-parent `UNIQUE` constraint. Enforced identically at
three layers: the Postgres `CHECK` (migration `0010`), `JournalEntry.
__post_init__` → `validate_exactly_one_reference` (domain layer, raising
the same `UnprocessableEntityError`/`UNPROCESSABLE_ENTITY` shape
`TagMistakeUseCase` already established, Sprint 4.3 — no numbered
`INV-JOURNAL-*` invariant exists, confirmed absent from `TRADEOS_DOMAIN_
MODEL.md` §14-15), and Pydantic's own shape validation at the boundary.

### Resolved by precedent, not invention

- **Reference type is immutable after creation** — explicitly stated
  across three documents ("changing what an entry is 'about' is modeled
  as delete-and-recreate, not an edit"): `UpdateJournalEntryUseCase`
  accepts `content` only; `trade_id`/`period_start`/`period_end` have no
  edit path at all, not even one silently ignored.
- **No length limit on `content`, no markdown/rich-text, no title/tags**
  — confirmed by exhaustive absence across the Domain Model, Database
  Design, API Specification, and Technical Stack documents. `content` is
  a plain `TEXT`, rendered as plain text (React's default escaping — no
  `dangerouslySetInnerHTML` anywhere in this feature).
- **No `period_end >= period_start` ordering check** — the backend's own
  check constraint doesn't enforce one, so neither the domain layer nor
  the frontend Zod schema invents one either; documented explicitly in
  both `journal_entry.py` and `journal/schemas.ts` as a deliberate
  absence, not an oversight.
- **`DELETE` is idempotent** — `TRADEOS_API_SPECIFICATION.md` §3.4's
  general HTTP-verb-semantics rule ("Soft-delete... Idempotent: Yes"),
  same as `DeleteTradeUseCase` already applies: deleting an
  already-deleted entry is a successful no-op, never a `404`.
- **`Idempotency-Key` supported on `POST /journal-entries`** — §3.6's
  general rule ("every POST that creates a resource") applied via the
  same `app/platform/idempotency.py` helper `POST /trades` already uses;
  the Journal section of the API spec doesn't restate this locally, but
  neither does any other module's endpoint section — the general rule
  governs.

### Architecture: `journal` reads `trading` through an Application-layer factory, never its repository directly

First implementation attempt imported `TradeRepository` straight from
`trading.infrastructure.repository` into `CreateJournalEntryUseCase` and
the router — caught during the audit pass as a violation of this
codebase's own established cross-module discipline
(`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3, Forbidden Dependencies): every
prior cross-module read (`RegisterTradeUseCase` resolving a
`CatalogEntry` via Configuration's `build_get_catalog_entry_use_case`)
goes through the *target* module's own Application-layer factory, never
its repository or domain directly. Fixed by adding
`backend/app/modules/trading/application/get_trade_by_id.py`
(`GetTradeByIdUseCase` + `build_get_trade_by_id_use_case`) — a small,
new, pure-read Use Case mirroring `GetCatalogEntryUseCase`'s own
docstring almost verbatim — and wiring Journal through that instead.
`Trading` still depends on nothing from `Journal` (per Backend Blueprint
§3.10 and System Architecture §4, the dependency runs one way only).

### Frontend: pages are this architecture's own composition points (`eslint.config.js` refinement)

`TradeDetailPage`'s own wireframe (`TRADEOS_FRONTEND_BLUEPRINT.md` §8.3)
assembles `TradeSummaryCard`/`EvaluationSummaryCard`/`MistakesCard`
(Trading's own) alongside `JournalEntriesCard` — which, unlike
`MistakesCard`, is backed by a genuinely separate feature module
(`journal`, its own `api.ts`/`types.ts`/`queryKeys.ts`), not Trading's
own endpoints. The `eslint-plugin-boundaries` rule built in the prior
sprint correctly flagged this as a `trading → journal` violation —
confirmed as a real architectural question, not a business one, so
resolved by extending (not weakening) the existing composition-root
precedent: a new `page` element (`src/features/*/pages`, matched *before*
the broader `feature` pattern) is permitted to import from any feature or
shared layer, mirroring the composition root's own stated rationale
("legitimately need to import from every feature to wire the app
together") applied one level down, to a single page instead of the whole
app. Everything else in a feature — `components/`, `api.ts`, `types.ts`,
`hooks/` — stays exactly as isolated as before. Verified with the same
smoke-test method as the original boundaries setup: a temporary
cross-feature import from a `pages/*` file confirmed allowed, the
identical import from a `components/*` file confirmed still rejected,
both removed after confirming.

`JournalEntriesCard` itself lives in `features/journal/components/` (not
`features/trading/components/`), since it owns Journal's own read/write
logic — `TradeDetailPage` imports it directly, the one place in this
architecture now permitted to do so.

### A real bug caught by E2E, not written into the app

`JournalEntryForm`'s period-scoped fields and `JournalListPage`'s own
date-range filter both originally used `id="period_start"`/
`id="period_end"`. When the "+ New Entry" modal is open on the Journal
List page, both sets of inputs are mounted simultaneously — duplicate
DOM IDs broke `<label htmlFor>` association, which `e2e/journal.spec.ts`
caught immediately (`getByLabel("Period Start")` timing out, confirmed
via the page snapshot: the input existed but carried no accessible
name). Fixed by renaming the modal's fields to `entry_period_start`/
`entry_period_end`.

### Added
- Backend: `backend/alembic/versions/0010_create_journal_schema.py`;
  `app/modules/journal/{domain/journal_entry.py,infrastructure/{models,
  repository}.py,application/{create,get,list,update,delete}_journal_
  entry.py,presentation/{schemas,router,pagination}.py}`;
  `app/modules/trading/application/get_trade_by_id.py`; router registered
  in `app/main.py`; `tests/journal/test_journal_flow.py` (28 tests).
  `tests/conftest.py` and the four dedicated-engine concurrency test
  files (`tests/platform/test_idempotency_concurrency.py`,
  `tests/configuration/test_publish_concurrency.py`,
  `tests/configuration/test_seed_bias_engine.py`,
  `tests/trading/test_reevaluate_concurrency.py`) updated to create the
  new `journal` schema — `Base.metadata` is process-wide, so every test
  file's own `create_all` needed it once `journal_models` was imported
  anywhere.
- Frontend: `src/features/journal/{types,api,queryKeys,schemas}.ts`
  (+ `schemas.test.ts`); `components/{JournalEntryForm,
  JournalEntriesCard}.tsx` (+ `JournalEntryForm.test.tsx`);
  `pages/{JournalListPage,JournalEntryDetailPage}.tsx` (replacing the old
  `JournalPage.tsx` placeholder). `src/features/trading/pages/
  TradeDetailPage.tsx` updated to render `JournalEntriesCard` in place of
  its own placeholder. New routes: `/journal`, `/journal/:entryId`
  (`src/router.tsx`). `eslint.config.js`: new `page` element + policy.
- `e2e/journal.spec.ts` (3 tests).

### Verification performed
- Backend: `pytest` — **267 passed** (28 new; 239 carried over); `ruff
  format --check` / `ruff check` / `mypy app` — clean (167 source files).
- Frontend: `tsc --noEmit` — clean; `eslint .` — clean, zero warnings,
  zero `boundaries/dependencies` violations (including the new `page`
  element, smoke-tested both directions); `vitest run` — **66 passed**
  (12 test files, 12 new); `vite build` — succeeds (317 modules).
- E2E: `playwright test` — **17 tests, 16 passed, 1 pre-existing
  documented flake** (the same `evaluation-preview.spec.ts` Configuration-
  publish race already recorded in the prior entry, reconfirmed unrelated
  via isolated re-run) — including all 3 new `journal.spec.ts` tests and
  the full pre-existing suite, zero regressions.
- Audit: `grep` confirms zero TODO/FIXME in any new file, zero
  `console.log`; the first-attempt cross-module violation
  (`journal → trading.infrastructure` direct import) was caught and
  fixed before this pass, not left in; the local dev stack (Postgres
  container, `uvicorn` process) spun up only for this verification was
  torn down afterward.

### Confirmation
No `git push` was run at any point.

## Sprint 5.2 — Mistakes Ranking Backend + Frontend

`MistakePriorityRankingService`; the Mistakes Ranking page —
`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Sprint 5.2, closing Milestone M5
("Journal entries... and the Mistake priority ranking both function
against real Trade data"). Pre-analysis re-read `TRADEOS_DOMAIN_MODEL.md`
§4.6/§8.7/§8.9/§11/§12.3/§14, `TRADEOS_BACKEND_BLUEPRINT.md` §3.8/§4.6/
§4.8/§5/§6/§19-21, `TRADEOS_API_SPECIFICATION.md` §5/§6.4/§6.9/§7.4,
`TRADEOS_FRONTEND_BLUEPRINT.md` §3/§4.1/§4.7/§5.3/§5.7/§6.7/§7/§8/§11/§12,
`TRADEOS_PRODUCT_BIBLE.md` §9/§15, `TRADEOS_DATABASE_DESIGN.md` §3/§5/
§6.8/§6.9/§6.14, and ADR-04 — plus the actual repo state (`backend/app/
modules/mistakes/` was empty scaffolding; `frontend/src/features/
mistakes/` held only a placeholder page; both routes/nav already wired).

### A real, unregistered documentary gap — stopped and asked before writing code

Every document that mentions `MistakePriorityRankingService` (Domain
Model §12.3, §8.9; Product Bible §9; Backend Blueprint §3.8/§5; API Spec
§6.9; Frontend Blueprint §11/§12) repeats the same three nouns —
*frequency, cost, priority* — without ever defining any of them
mathematically. Unlike the `scoring_profile`/`closed_at` precedents from
Sprint 4.1, this gap was never even registered as a tracked open
question anywhere (checked Product Bible §15, API Spec §18's API-1
through API-6, Backend Blueprint §21's BE-1 through BE-10 in full — none
of them). `trade_mistakes` stores no cost data of its own (§6.14: only
`trade_id, catalog_entry_id, created_at`), so "cost" had to be derived
from the tagged Trade — and even that had two undecided candidates
(`realized_pnl` vs. the never-stored, computed `r_multiple`). Stopped
and asked before writing any ranking code; your approved resolution:

- **Cost** = sum of `r_multiple` (risk-normalized, consistent with the
  app's existing scoring/evaluation language), never `realized_pnl`.
- **Scope** = every Trade tagged with a mistake, winners included — not
  losses-only.
- **Aggregation** = total (sum), matching the documents' own literal
  "total cost" wording, not an average per occurrence.
- **Priority** = explicitly **not** a combined formula. Your correction
  to my first proposal (`priority = frequency × |cost|`): Priority must
  be a **stable** rank by the system's primary metric (Cost, the default
  sort), fixed regardless of which column the user temporarily sorts the
  *visible* table by — otherwise "Priority" degrades into a duplicate of
  the current row index, carrying no information of its own. Implemented
  exactly that: `rank_mistakes()` assigns each tag a `priority` (its
  1-indexed rank by `total_cost_r` ascending) once; `sort` only reorders
  the returned list for display, never touches an entry's own `priority`
  value. Verified by a dedicated backend test and an E2E test, both
  asserting the same tag's `priority` is byte-identical across two
  different active sorts.

Two secondary ambiguities resolved without needing a question: pagination
(API Spec never says whether `/mistakes/ranking` is a paginated "list
endpoint" like Trades/Journal or a single computed object like
Statistics; resolved by precedent — architecturally identical to
Statistics' on-demand, never-cached computation per ADR-04/KDD-04, not to
a growing row-scale collection — a bare unpaginated array, same
precedent as `/configuration/scoring-criteria`); and deactivated tags
(the Master Plan's own regression-test note, "excludes deactivated tags'
*new* use while still counting their historical occurrences," is a
direct consequence of DI-09/DI-10 already enforced by `TagMistakeUseCase`
— this sprint's only obligation was to never filter a deactivated tag
out of the ranking, confirmed by a dedicated test).

Two broken internal citations noted, not corrected: the Master Plan cites
Frontend Blueprint §6.10–6.11 for this page, but those sections are
"Reflect (Journal)" and "Manage Catalogs" — unrelated; and Backend
Blueprint §20 cites its own nonexistent "§5.3" (Section 5 has no
subsections).

### Architecture: one-way dependency, zero new persistence

`Mistakes` reads `Trading` and `Configuration` exclusively through each
module's own Application-layer factory (`ListMistakeOccurrencesUseCase`
+ `build_list_mistake_occurrences_use_case`, new; `ListCatalogEntriesUseCase`
gained `build_list_catalog_entries_use_case`, which didn't exist yet) —
never a repository directly, same discipline (re-)established in Sprint
5.1. Neither `Trading` nor `Configuration` imports anything from
`Mistakes` — confirmed by `grep`, zero results. `compute_r_multiple` was
extracted from `Trade.r_multiple` into a standalone function (behavior
unchanged, confirmed by the full `tests/trading/` suite) so the ranking
can compute cost directly from a batched query's raw fields without
constructing a full `Trade` per row. `TradeMistakeRepository.
list_trade_facts_for_ranking` does the aggregation-enabling work in one
JOIN query (`trade_mistakes` + `trades`, scoped to `user_id`), avoiding
the N+1 an approach iterating `TradeRepository.list_all` +
per-trade `list_by_trade_id` would produce. No new table, no migration —
`Mistakes` owns no persistence, per Backend Blueprint §3.8 exactly.

### A real sort-direction bug, caught by its own test before shipping

The first implementation of `sort=-cost` used `total_cost_r is not None`
as its null-ordering flag — inverted from `sort=cost`'s `is None` — which
put still-open trades' tags (no computable cost) *first* instead of last
when sorting descending. Caught immediately by
`test_priority_is_stable_across_different_sort_orders`, the same test
built to verify the core architectural requirement above. Fixed by using
the identical "`None` always sorts last, in both directions" flag for
both `cost` and `-cost`.

### Added
- Backend: `backend/app/modules/mistakes/{domain/mistake_ranking.py,
  application/get_mistake_ranking.py,presentation/{schemas,router}.py}`;
  `app/modules/trading/application/list_mistake_occurrences.py`;
  `TradeMistakeRepository.list_trade_facts_for_ranking` +
  `MistakeTradeFact` (`trading/infrastructure/repository.py`);
  `compute_r_multiple` extracted in `trading/domain/trade.py`;
  `build_list_catalog_entries_use_case`
  (`configuration/application/list_catalog_entries.py`); router
  registered in `app/main.py`; `tests/mistakes/test_mistake_ranking_flow.py`
  (8 tests).
- Frontend: `src/features/mistakes/{types,api,queryKeys}.ts`;
  `pages/MistakesRankingPage.tsx` (replacing the old `MistakesPage.tsx`
  placeholder) — table only, per approved scope; the "Mistakes Frequency/
  Cost" chart (Frontend Blueprint §12) stays deferred with the rest of
  this project's charting infrastructure (Recharts). `src/router.tsx`
  updated, same `/mistakes` path.
- `e2e/mistakes.spec.ts` (2 tests) — including a dedicated assertion that
  Priority is unchanged in the real UI after switching the visible sort
  from Cost to Frequency.

### Verification performed
- Backend: `pytest` — **283 passed** (8 new; 275 carried over, one
  `test_tampered_signature_is_rejected` flake observed during a
  full-suite run, confirmed unrelated to this sprint and non-reproducing
  via two clean full-suite re-runs); `ruff format --check` / `ruff check`
  / `mypy app` — clean (172 source files).
- Frontend: `tsc --noEmit` — clean; `eslint .` — clean, zero warnings,
  zero `boundaries/dependencies` violations; `vitest run` — **66 passed**
  (12 test files, no regressions); `vite build` — succeeds (319 modules).
- E2E: `playwright test` — **19 tests, 18 passed, 1 pre-existing
  documented flake** (the same `evaluation-preview.spec.ts` Configuration-
  publish race, reconfirmed unrelated) — including both new
  `mistakes.spec.ts` tests.
- Audit: `grep` confirms zero TODO/FIXME, zero `console.log`, zero
  imports of `mistakes` from `trading`/`configuration` (correct
  one-way dependency direction); the local dev stack (Postgres container
  — which had crashed mid-session on an unrelated Docker Desktop
  restart, diagnosed via a direct `curl` against a DB-touching endpoint
  before blaming the E2E tests themselves, then restarted — and the
  `uvicorn` process) was torn down after verification.

### Confirmation
No `git push` was run at any point.

## Sprint 6.1 — Statistics Overview & By-Dimension

`StatisticsAggregationService`'s all-time computation — `TRADEOS_
IMPLEMENTATION_MASTER_PLAN.md` Sprint 6.1. Backend only:
`GET /statistics/overview`, `GET /statistics/by-dimension`. Rolling
Statistics and the frontend are Sprint 6.2. Pre-analysis re-read
`TRADEOS_DOMAIN_MODEL.md` §2.3/§4.5/§9/§11/§12.2/§14-15/KDD-04,
`TRADEOS_BACKEND_BLUEPRINT.md` §3.9/§4.8/§5/§6/§19-21, `TRADEOS_API_
SPECIFICATION.md` §5/§6.10/§7.4/§18-19, `TRADEOS_FRONTEND_BLUEPRINT.md`
§4.2/§5.6/§8.6/§11/§12/§20, `TRADEOS_PRODUCT_BIBLE.md` §4.2/§7/§9/
§10.1-10.2/§12.2/§15, `TRADEOS_DATABASE_DESIGN.md` §3/§6.9/§6.12/§10.2,
ADR-04, and the actual repo state.

### Three genuine gaps, none previously registered as an open question anywhere

Win Rate and Total P&L turned out to be precisely defined by literal
citation ("the proportion of closed Trades that resulted in TP" —
resolving even the break-even question directly: BE is closed, so it's
in the denominator, but never the numerator). Expectancy, Profit Factor,
and by-dimension's null-bucket behavior were not — confirmed absent
across every numbered open question in all seven frozen documents
(Product Bible §15, API Spec §18, Backend Blueprint §21's BE-1 through
BE-10) before stopping to ask. Your approved resolutions:

- **Expectancy** = **Average R** = mean of `r_multiple` across every
  closed Trade (open Trades excluded; break-even Trades participate with
  their own real, usually-near-zero `r_multiple`). The two Domain-Model-
  named metrics are numerically identical under this formula — both
  fields still exist in the response, since the Domain Model names them
  as two separate outputs.
- **Profit Factor** = `gross_profit_r / gross_loss_r`, R-multiple-based
  (never `realized_pnl`-based — consistent with Expectancy/Average R,
  same reasoning Sprint 5.2 approved for Mistakes' "cost"). Zero gross
  loss → `None`, never `Infinity`/`NaN`/an exception — the same
  convention `compute_r_multiple` already established for its own
  division.
- **Null-dimension bucketing**: a Trade with no `strategy_id`/`setup_id`/
  `session_id` groups into an explicit `"unassigned"` bucket in
  `GET /statistics/by-dimension` — never silently dropped from the
  aggregation. `direction` never produces this bucket (it's never `NULL`
  on a Trade).

Two secondary ambiguities resolved without a question, by direct
reasoning (not circular precedent): pagination — a bare, unwrapped JSON
object (`overview`) / array (`by-dimension`), architecturally identical
to Mistakes Ranking's own on-demand, never-cached computation
(ADR-04/KDD-04), confirmed by API Spec §6.10's "pure reads with no side
effects and no persisted result" and §7.4's envelope being scoped to
"list endpoint[s]" (Statistics is never called one); and Win Rate's raw
0-1 ratio (never pre-multiplied by 100), same convention `Trade.
captured_pct` already established.

### A documentary contradiction resolved by weight of evidence, not by asking

Backend Blueprint §6 (Repository Blueprint) names only `TradeRepository`/
`CatalogRepository` as Statistics' read paths, never mentioning
Evaluation — apparently contradicting §3.9's own "Dependencies: Trading,
Evaluation (both read-only)," API Spec §19 ("reads `trading` +
`evaluation` data"), ADR-04 ("computed fresh from Trading + Evaluation
data"), and the Frontend Blueprint's own wireframe requiring "engine
averages." Resolved without asking: `EvaluationSnapshotRepository`
already lives inside `trading/infrastructure/repository.py` (established
since Sprint 4.1 — `evaluation_snapshots` is a `trading`-schema table,
not a separate module's schema), so "reading Trading + Evaluation" and
"reading only through `TradeRepository`" describe the exact same thing
at the code level — the Repository Blueprint's omission is an incomplete
enumeration, not a deliberate exclusion.

Three more broken/loose citations noted, not corrected: API Spec §6
promises `GET /statistics/by-dimension` "full prose detail" (one of only
8 endpoints named that way) but §6.10 delivers a bare 3-row table with an
empty Notes cell; Backend Blueprint §20's Statistics row cites its own
nonexistent "§5.2" (Section 5 has no subsections — the same class of
defect as the "§5.3"/"§6.10-6.11" citations already flagged in the
Sprint 5.1/5.2 entries, this time newly caught for a row nobody had
checked yet); and Domain Model §4.5/Product Bible §9 both list a "time"
dimension no operational document (Master Plan, API Spec, Frontend
Blueprint) actually implements — the real `by-dimension` enum stays at
exactly four values (strategy/setup/session/direction), consistent
everywhere it's operationally defined; `entry_trigger` was confirmed
excluded the same way.

### Architecture

Two-query, zero-N+1 design, mirroring Sprint 5.2's `list_trade_facts_
for_ranking` precedent exactly: `TradeRepository.list_all_facts_for_
statistics(user_id)` (one unbounded query — deliberately not `list_all`,
which is cursor-paginated and capped) + `EvaluationSnapshotRepository.
list_current_by_trade_ids` (already existed since Sprint 4.1, reused
unchanged) — combined by a new `ListTradeStatisticsFactsUseCase`
(Trading's own Application layer), exposed to Statistics via
`build_list_trade_statistics_facts_use_case`, never a repository
directly. Catalog names for `strategy`/`setup`/`session` groups resolve
through `build_list_catalog_entries_use_case` (Sprint 5.2, unchanged).
`Configuration`'s `list_catalog_entries.py` and `Trading`'s own domain/
infrastructure files are the only pre-existing files touched; neither
`Trading` nor `Configuration` imports anything from `Statistics` —
confirmed by `grep`, zero results. All aggregation math lives in one
pure, dependency-free module (`statistics/domain/statistics_aggregation.py`
— no repository access, no SQL, no FastAPI import anywhere in it);
`GetStatisticsOverviewUseCase`/`GetStatisticsByDimensionUseCase` only
orchestrate, never compute. No new table, no migration, no cache, no new
dependency — `Statistics` owns no persistence, per Backend Blueprint
§3.9 exactly.

### A real discovery, not a bug: engine scores are 0, never `None`, with zero criteria configured

The first version of `test_overview_averages_engine_scores_skipping_none`
asserted an engine with no criteria configured would average to `None`.
It returned `0.0` instead — traced to `score_quality`'s own signature
(and every other engine's), which always returns a real `Score`, never
`None`; a weighted sum over zero criteria is legitimately `0`, not "not
yet computable." Confirmed this is correct, existing behavior (`evaluation_
snapshots`' nullable score columns exist only for a *future* sixth engine
that wouldn't exist on historical snapshots, never for today's five,
which always compute). Fixed the test's expectation, not the code, and
added a dedicated pure-domain unit test (`test_statistics_aggregation.py`,
mirroring the `tests/evaluation/test_confidence_engine.py` precedent) to
exercise the genuine `None`-skip path directly, since today's real system
never produces one through the HTTP stack to test against.

### Added
- Backend: `backend/app/modules/statistics/{domain/statistics_
  aggregation.py,application/{get_statistics_overview,get_statistics_by_
  dimension,mapping}.py,presentation/{schemas,router}.py}`;
  `app/modules/trading/application/list_trade_statistics_facts.py`;
  `TradeRepository.list_all_facts_for_statistics` + `TradeStatisticsFact`
  (`trading/infrastructure/repository.py`); router registered in
  `app/main.py`; `tests/statistics/{test_statistics_flow.py (21 tests,
  including the literal Exit Criteria — a hand-computed Win Rate/
  Expectancy over a controlled Trade set), test_statistics_aggregation.py
  (12 pure unit tests)}`.

### Verification performed
- `pytest` — **299 passed** (33 new; 266 carried over), zero
  regressions; `ruff format --check` / `ruff check` / `mypy app` — clean
  (179 source files).
- Audit: `grep` confirms zero TODO/FIXME, zero imports of `statistics`
  from `trading`/`configuration`/`journal`/`mistakes` (correct one-way
  dependency direction); zero changes to `pyproject.toml`/`poetry.lock`
  (no new dependency); zero new migrations, tables, indexes, or cache;
  zero frontend changes (confirmed by `git status`, matching this
  sprint's backend-only scope exactly); the local Postgres container
  spun up only for this verification was torn down afterward.

### Confirmation
No `git push` was run at any point.

## Sprint 6.2 — Rolling Statistics + Frontend

Phase 6 of the Implementation Master Plan, second and closing sprint.
Scope (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`): *"the configurable
moving-window comparison (`TRADEOS_DOMAIN_MODEL.md` §2.3); Statistics
page, all three tabs. Deliverables: `GET /statistics/rolling`; the full
Statistics page wired to all three endpoints. Exit Criteria: Milestone
M6 is achieved."* Milestone M6 (§7): *"Statistics Overview, By-Dimension,
and Rolling tabs all return figures that are independently verifiable by
hand-computing them from the same underlying Trades (DI-11)."*
**Milestone M6 is achieved.**

### No genuine business gap this sprint

The pre-analysis found every business question already resolved by
literal citation or by Sprint 6.1's own precedent — no `AskUserQuestion`
was needed:

- **Rolling's metrics** = exactly Overview's `StatisticsSummary` shape
  (API Spec §6.10: *"Same metrics, computed over the most recent
  `?window=` Trades, alongside the all-time comparison"*) — explicitly
  **not** the original Excel's 26-metric Rolling Statistics sheet
  (Performance/Risk/Evaluation/Psychology, `01_PROJECT_AUDIT.md`), a
  simplification the frozen API Spec itself already made, not one
  invented here.
- **Window enum** = `{10, 20, 30, 50, 100, 200}`, a closed set (API
  Spec §6.10; Frontend Blueprint §5.6/§8.6, identical) — validated at
  the router exactly like `dimension`, 422 on any other value, no
  default (required query param), same precedent `dimension: str =
  Query(...)` already established in Sprint 6.1.
- **Window membership** = the `window` most recent Trades by
  `entered_at` (Database Design: indexed specifically for *"Analytics'
  time-based queries"*), drawn from every non-deleted Trade — open
  Trades included, exactly like Overview/By-Dimension already handle
  "open" internally per metric. Selecting the window is pure data
  selection, not a new formula: the exact same `aggregate_statistics`
  Sprint 6.1 built runs unchanged over the windowed subset and over the
  full set.
- **"All-time comparison"** = `aggregate_statistics` over the complete,
  unwindowed fact list — numerically identical to what `GET
  /statistics/overview` returns for the same user at the same moment,
  never a different "older-than-the-window" baseline (Domain Model §2.3:
  *"compared against all-time performance"*).
- **Response field names `rolling`/`overall`** — not invented: the
  literal terminology the frozen documents themselves repeat ("Rolling
  vs. Overall Comparison," Frontend Blueprint §12/§8.6; "Rolling vs.
  Overall," `01_PROJECT_AUDIT.md`).
- **Charting library** — `10_TRADEOS_TECHNICAL_STACK.md` §6.8 mandates
  **Recharts**, resolving what first looked like a real gap (the
  Frontend Blueprint §12 explicitly declines to choose one: *"Describing
  communication purpose, not a chosen charting library"*). Confirmed
  before writing any frontend code, not assumed.
- **Use Case name** — Backend Blueprint's own compact rows name it
  `GetRollingStatistics` (alongside `GetStatisticsOverview`/
  `GetStatisticsByDimension`); implemented as `GetRollingStatisticsUseCase`
  for full-word consistency with its two siblings.

### Architecture

Domain: `StatisticsFact` gained one field, `entered_at: datetime` (plain
data, not I/O — same precedent as `Trade`'s own domain dataclass already
carrying timestamps); two new pure functions in `statistics_aggregation.py`
— `select_rolling_window(facts, window)` (sort-and-slice, no formula) and
`aggregate_rolling(facts, window)` (composes the *existing*
`aggregate_statistics` twice, once per subset — no new math). Trading:
`TradeRepository.list_all_facts_for_statistics`'s existing SELECT gained
one already-indexed column (`entered_at`); `TradeStatisticsFact`/
`TradeStatisticsRecord` pass it through — zero new queries, zero N+1.
Application: `GetRollingStatisticsUseCase` (new, mirrors `GetStatisticsOverviewUseCase`
exactly — pure orchestration, no formula, resolves facts via `ListTradeStatisticsFactsUseCase`,
never a repository directly). Presentation: `GET /statistics/rolling`
added to the existing router; `RollingStatisticsResponse` added to the
existing schemas file. Confirmed by `grep`: `statistics` still never
imports a `trading`/`configuration` repository directly (factories only);
`trading`/`configuration`/`journal`/`mistakes` still never import
`statistics` (one-way dependency direction intact). Zero new tables,
migrations, indexes, cache, or backend dependency.

Frontend: `src/features/statistics/{types,api,queryKeys,format,chartColors}.ts`
+ `components/{MetricBarChart,OverviewTab,ByDimensionTab,RollingTab}.tsx`
+ `pages/StatisticsPage.tsx` (three `Tabs`, per confirmed endpoint —
Frontend Blueprint §4.2: *"never a tab with no backing endpoint"*).
`src/components/MetricCard.tsx` — new shared component, first real
consumer of something the Frontend Blueprint §7 had described but no
sprint had built yet (Sprint 6.1 was backend-only). One reusable chart
component, `MetricBarChart`, instantiated once per metric named in
§12's "Displayed Metrics" columns (3× for By Dimension: Win Rate,
Expectancy, Profit Factor; 4× for Rolling: Win Rate, Expectancy, Profit
Factor, Average R) rather than one multi-metric chart — a 0-1 ratio, an
unbounded R-multiple, and a ratio that can exceed 1 do not belong on one
shared axis (the "never a dual-axis chart" rule, applied to bars).
Identity (Rolling vs. Overall; by-dimension group) is always carried by
the x-axis category label, never by color alone. Each tab also renders a
`DataTable` with the complete field set, not just the charted subset.

### Chart color decision (documented, not silently chosen)

The project's Design System (`src/design-system/tokens.css`) defines
only `accent` and `danger` — no second categorical hue exists for a
genuine two-series comparison (Rolling vs. Overall). Rather than add a
new Design System token (the same restraint `Badge.tsx` already
documented for itself) or eyeball a second color, ran the dataviz
skill's `validate_palette.js` against the app's real accent (`#6366F1`)
paired with a candidate orange (`#d95926`) on the app's actual dark
surface (`#141418`): all checks passed (CVD ΔE 30.3, normal-vision ΔE
33.3, both well clear of the 8/15 floors). `ROLLING_COLOR` reuses the
existing `--color-accent` CSS variable; `OVERALL_COLOR` is that one
validated hex, documented in `chartColors.ts` — no other new color
introduced anywhere.

### A build-size consequence, addressed directly

Adding Recharts (first real consumer in this project) pushed the single
production bundle to 936 kB, past Vite's 500 kB warning — the app had
never lazy-loaded any route before this sprint (`grep` confirmed zero
`React.lazy` usage anywhere in `router.tsx`), despite Frontend Blueprint
§2.4/§16 already calling for per-feature code splitting. Rather than
silently accept the regression or retrofit every existing route (out of
this sprint's scope), lazy-loaded only the `/statistics` route
(`React.lazy` + `Suspense`, Vite's own recommended fix) — Statistics now
ships as its own 367 kB chunk, and the shared main bundle actually
*shrank* to 568 kB relative to before this sprint's change (that
residual is every other still-unsplit route, pre-existing, out of
scope). Noted as pre-existing technical debt, not fixed further here.

### Documentary defects noted, not corrected

Backend Blueprint's compact traceability row names the new Use Case
`GetRollingStatistics` in one place while its own service-table row
group-names all three as `GetStatisticsOverview/ByDimension/Rolling` —
a minor prefix inconsistency, not a contradiction; the fuller name
(`GetRollingStatisticsUseCase`) was kept for consistency with its two
already-shipped siblings. Frontend Blueprint §7 (Component Blueprint)
never lists "Chart" among its own enumerated reusable components, even
though §8 and §12 both reference it repeatedly ("Chart — By-Dimension
Comparison," "Chart — Rolling vs. Overall Comparison") — an omission in
the enumeration, not a deliberate exclusion.

### Explicit exclusions (approved scope)

Row-click drill-down from a by-dimension group into a filtered Trades
List or Playbook Setup (Frontend Blueprint §12/§18) — named in the
Blueprint but not itemized in this sprint's approved deliverable list;
deferred to whichever future sprint actually builds Playbook/Trades-List
filter wiring. Dimension+window combination — the Rolling tab has no
dimension selector anywhere in the Blueprint's own wireframe. Export,
Equity Curve — already-registered Open Questions (FE-6, FE-7),
unaffected by this sprint.

### Added
- Backend: `app/modules/statistics/application/get_rolling_statistics.py`
  (new); `ROLLING_WINDOWS`, `RollingStatistics`, `select_rolling_window`,
  `aggregate_rolling` (`statistics/domain/statistics_aggregation.py`);
  `RollingStatisticsResponse` (`statistics/presentation/schemas.py`);
  `GET /statistics/rolling` (`statistics/presentation/router.py`);
  `entered_at` added to `StatisticsFact`, `TradeStatisticsFact`,
  `TradeStatisticsRecord`. Tests: 10 new unit tests
  (`test_statistics_aggregation.py`, now 26) covering window selection at
  sizes the real endpoint can never accept (2, 3) plus the boundary
  cases; 5 new integration tests (`test_statistics_flow.py`, now 23)
  including the literal Exit Criteria test — 2 older losing Trades
  followed by 10 newer winning Trades, `rolling` (window=10) hand-verified
  to reflect only the 10 winners, `overall` hand-verified to reflect all
  12.
- Frontend: `src/components/MetricCard.tsx` (new shared component);
  `src/features/statistics/` — `types.ts`, `api.ts`, `queryKeys.ts`,
  `format.ts` (+ `format.test.ts`, 7 unit tests), `chartColors.ts`,
  `components/{MetricBarChart,OverviewTab,ByDimensionTab,RollingTab}.tsx`,
  `pages/StatisticsPage.tsx` (rewritten from its Sprint-6.1-era
  placeholder); `router.tsx` — `/statistics` now lazy-loaded;
  `e2e/statistics.spec.ts` (2 tests). `recharts` added as a new
  dependency — mandatory per `TRADEOS_TECHNICAL_STACK.md` §6.8, its
  first real consumer in this project.

### Verification performed
- Backend: `pytest` — **309 passed** (10 new; 299 carried over), zero
  regressions; `ruff format --check` / `ruff check` / `mypy app` —
  clean (180 source files). Audit: zero TODO/FIXME; `grep` confirms
  `statistics` never imports a `trading`/`configuration` repository
  directly and is never imported back by any other module; zero changes
  to `pyproject.toml`/`poetry.lock`; zero new migrations, tables,
  indexes, or cache.
- Frontend: `tsc -b --noEmit` — clean; `eslint .` — clean (feature
  boundaries respected, no new rule violations); `vitest run` — **73
  passed** (7 new; 66 carried over); `vite build` — succeeds,
  `/statistics` isolated into its own 367 kB lazy chunk. Audit: zero
  `console.log`/TODO/FIXME in any new file.
- E2E: real stack (Docker Postgres 16 + `uvicorn` + Chromium/Playwright,
  never mocked) — `e2e/statistics.spec.ts` (2/2 passed): the three tabs
  each read correctly off one registered, closed Trade, including the
  "Unassigned" by-dimension bucket and the Rolling/Overall table reading
  identically when only one Trade exists. Full suite: **20/21 passed** on
  the first parallel run; the one failure
  (`configuration-and-catalogs.spec.ts`, unrelated to this sprint) passed
  cleanly on an isolated re-run — a pre-existing parallel-worker flake in
  registration timing, not a regression introduced here. Dev stack
  (Postgres container, `uvicorn`) torn down afterward.

### Confirmation
No `git push` was run at any point.

## Sprint 7.1 — Playbook Backend

Phase 7 of the Implementation Master Plan, first sprint — the last
confirmed Bounded Context module. Scope
(`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`): *"`PlaybookSetup` CRUD,
attachments, 1:1 linkage to a `kind=setup` Catalog entry. Deliverables:
Playbook definitions manageable via the API; performance data explicitly
never stored on the setup itself, always a live Statistics read. Exit
Criteria: a Playbook Setup's performance figures match the equivalent
Statistics by-dimension query for that same Setup, exactly."*
`PlaybookRecommendationService` (named only in Phase 7's broader
narrative, not in this sprint's own bullet, and confirmed by Known Gap
BE-4 to have no confirmed endpoint) is explicitly out of scope.

### No genuine business gap this sprint

Pre-analysis resolved every question by literal citation or by
established precedent — no `AskUserQuestion` was needed:

- **`PlaybookSetup` is global, not scoped by `user_id`** — API Spec line
  101, cited literally: *"PlaybookSetup are, today, global to the single
  user — not yet modeled as owned by anyone specifically."* First module
  in this project without per-user ownership filtering.
- **Attachments persist only a caller-supplied reference, never file
  bytes** — cross-checked across three documents: Database Design §6.16
  ("the actual file lives in object storage... this schema stores only
  the reference"), Technical Stack §6.12 (object storage provider
  unchosen, Open Question OQ-6), and the Master Plan's own §16 blocking-
  questions list, which excludes OQ-6 entirely — if Phase 7 needed real
  file storage, it would be listed there as blocking, the way OQ-1/OQ-4
  block Phase 9.
- **No `DELETE /playbook-setups/{id}`** — not in the confirmed endpoint
  table (§6.8); Domain Model §13.4's lifecycle is `Active -> Deprecated`
  only, no third state.
- **422, not `is_active`, gates creation** — the literal citation lists
  exactly two conditions ("not `kind=setup`," "already linked"); no
  active-status check exists here, deliberately diverging from
  `TagMistakeUseCase`'s superficially similar but differently-scoped
  check.
- **`name` is not a `PlaybookSetup` column** — Domain Model §8.8 calls it
  "Owned Information," but Database Design §6.15's real column list has
  neither `name` nor `description` (a documentary contradiction, noted
  not corrected). Resolved by precedent: `name` is resolved transitively
  from `catalog_entries.name`, the exact pattern `GetMistakeRankingUseCase`
  already established (Sprint 5.2).
- **`PlaybookSetupUpdated` fires on Update/Deprecate, never Create** — no
  document names a "Created" event for Playbook anywhere, unlike
  Trading's explicit `TradeRegistered`/`TradeAmended` split.

### Architecture

Domain: `PlaybookSetup`, `PlaybookSetupAttachment` — plain dataclasses,
no numbered Domain Invariant exists for either, so neither has a
`__post_init__` validator (a deliberate absence, not an oversight — the
four text fields are mutually independent). Application: 7 Use Cases
(`Create`/`Update`/`Deprecate`/`Get`/`List` `PlaybookSetup`,
`Add`/`Delete` attachment), each doing orchestration only. Infrastructure:
`PlaybookSetupRepository`/`PlaybookSetupAttachmentRepository`, zero
`user_id` filtering anywhere (the one deliberate architectural departure
from every other module). Presentation: 7 endpoints exactly matching API
Spec §6.8, cursor pagination for `GET /playbook-setups` (a real persisted
collection, not exempted like Mistakes/Statistics), `Idempotency-Key`
support on both resource-creating `POST`s.

Cross-module dependencies, both via `build_*` factories, never a
repository directly: `playbook -> configuration` (`build_get_catalog_entry_use_case`,
`build_list_catalog_entries_use_case`, both pre-existing, unchanged) and
`playbook -> statistics` (`build_get_statistics_by_dimension_use_case`,
**new** — Statistics' first cross-module consumer; added to
`get_statistics_by_dimension.py`, mirroring `build_list_trade_statistics_
facts_use_case`'s exact shape, with zero change to `GetStatisticsByDimensionUseCase`'s
own behavior or to any Statistics HTTP contract). Confirmed by `grep`:
`playbook` never imports `trading` directly; no module imports `playbook`
back (one-way dependency direction intact). Zero new backend dependency.

**Statistics composition, verified same-identifier by construction**:
`GetPlaybookSetupUseCase` calls `GetStatisticsByDimensionUseCase.execute(user_id,
"setup")` and selects the group where `group.dimension_value == str(setup.catalog_entry_id)`
— the identical UUID that gates the 1:1 link at creation time, so the
Exit Criteria ("match... exactly") holds by construction, not by
coincidence. No group found (no Trades yet) -> a locally-built all-`None`/
`total_pnl=0` `StatisticsSummary`, the same shape `aggregate_statistics([])`
already produces, never a different "no data" representation invented
here. Verified end-to-end by `test_exit_criteria_performance_matches_
statistics_by_dimension_exactly`, comparing all 10 `StatisticsSummary`
fields field-by-field against `GET /statistics/by-dimension` directly,
plus two independently hand-computed values.

### Bugs found and fixed during implementation

- **N+1 in the list endpoint's name resolution.** The first draft of
  `_resolve_names` looped over the page calling `GetCatalogEntryUseCase`
  once per setup, with an `if catalog_entry_id in names: continue` guard
  that looked like deduplication but never actually fired — every setup
  has a *distinct* `catalog_entry_id` (the 1:1 `UNIQUE` constraint
  guarantees it), so the guard was dead code and every row triggered its
  own query. Fixed before any test ran, by batching through
  `ListCatalogEntriesUseCase.execute("setup")` once per page (the exact
  pattern `GetStatisticsByDimensionUseCase` already uses for its own
  catalog-backed dimensions).
- **Missing `IntegrityError` -> `ConflictError` backstop on `Create`.**
  The pre-check (`get_by_catalog_entry_id`) alone cannot close a genuine
  concurrent-request race — two callers can both pass it before either
  commits. `CreatePlaybookSetupUseCase` initially had no `session` parameter
  and no `flush()`/`except IntegrityError` handling at all, unlike
  `TagMistakeUseCase`'s equivalent dual-layer check. Fixed by adding
  `session: AsyncSession` to the constructor and catching `IntegrityError`
  on flush, translating it to `ConflictError` (409) — caught by a
  dedicated real-concurrency test (`test_playbook_setup_concurrency.py`,
  a genuinely separate Postgres container and two truly concurrent
  transactions via `asyncio.gather`, same pattern as
  `test_publish_concurrency.py`) before being fixed.
- **A leftover `del user_id`** in both resource-creating endpoints,
  written while reasoning through "this resource has no ownership check"
  — but `user_id` is still needed to scope the `Idempotency-Key` claim
  (per authenticated caller, unrelated to resource ownership). Caught by
  re-reading the draft before running anything, not by a failing test.
- **Two test-authoring mistakes**, caught by the first test run, not by
  review: `GET /catalogs`'s actual response is a bare list, not a
  pagination envelope, breaking `test_deprecate_does_not_affect_the_
  linked_catalog_entrys_active_status`'s assumption; and the concurrency
  test's first draft asserted the loser must always raise `ConflictError`
  specifically, when `asyncio` scheduling can equally validly resolve
  the race as a clean, pre-check-caught `UnprocessableEntityError` (422)
  instead — both are correct "never two rows" outcomes, so the assertion
  was relaxed to accept either, with the real invariant (exactly one row
  ever exists) still checked directly against the database. Verified
  stable across 3 repeated runs after the fix.

### Documentary defects noted, not corrected

Domain Model §8.8 lists `name`/`description` as `PlaybookSetup`'s own
"Owned Information"; Database Design §6.15's actual schema has neither
column. Master Plan §8's Phase 7 narrative says "CRUD" generically;
the literal endpoint table (§6.8) has no `DELETE /playbook-setups/{id}`,
only `/deprecate` — resolved by cross-referencing Domain Model §13.4's
own lifecycle diagram (`Active -> Deprecated`, no third state).

### Added
- Backend: `app/modules/playbook/` — `domain/{playbook_setup,
  playbook_setup_attachment}.py`; `infrastructure/{models,repository}.py`;
  `application/{create,update,deprecate,get,list}_playbook_setup.py` +
  `application/{add,delete}_playbook_setup_attachment.py`;
  `presentation/{schemas,pagination,router}.py`. Migration `0011_create_
  playbook_schema.py` (`playbook` schema, `playbook_setups`,
  `playbook_setup_attachments`, no additional index beyond PK/UNIQUE —
  neither table's Database Design entry names one). `build_get_statistics_
  by_dimension_use_case` added to `statistics/application/get_statistics_
  by_dimension.py`. Router registered in `app/main.py`. Tests:
  `tests/playbook/test_playbook_setup_flow.py` (26 integration tests,
  including the literal Exit Criteria); `tests/playbook/test_playbook_
  setup_concurrency.py` (1 real-concurrency test, dedicated Postgres
  container).

### Verification performed
- `pytest` — **335 passed** (26 new; 309 carried over), zero regressions,
  concurrency test stable across 3 repeated runs; `ruff format --check` /
  `ruff check` / `mypy app` — clean (194 source files).
- Audit: zero TODO/FIXME; `grep` confirms `playbook` never imports
  `trading` directly and is never imported back by any other module
  (one-way dependency direction intact); zero changes to `pyproject.toml`/
  `poetry.lock` (no new dependency); zero print/debug statements; zero
  frontend changes (backend-only sprint, matching scope exactly). Dev
  Postgres container torn down after manual migration verification.

### Confirmation
No `git push` was run at any point.

## Sprint 7.2 — Playbook Frontend

Phase 7 of the Implementation Master Plan, closing sprint — Milestone M7
is achieved. Scope (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`): *"Playbook
List, Playbook Setup Detail pages. Deliverables: a trader can view and
edit setup documentation alongside genuinely live performance data."*

### No genuine business gap this sprint

- **Creation flow, not named in the Master Plan bullet or in either
  page's "Key API Dependency" column**: resolved by the direct precedent
  of Journal List (Sprint 5.1), whose own compact row is equally
  abbreviated yet still shipped a "+ New Entry" flow. Reinforced by the
  Empty State principle (§2.10): an empty list must always explain "what
  to do next," which requires a reachable create action.
- **Attachments UI**: a text/URL input for `file_reference`, never a
  real `<input type="file">`/upload — mechanically determined by Sprint
  7.1's already-frozen backend contract (a caller-supplied reference
  string only), cross-confirmed by OQ-6 (object storage provider)
  remaining unresolved and explicitly non-blocking for Phase 7.
- **`CatalogPickerModal` reused in place**, imported directly from
  `features/trading/components/` into Playbook's own page via the
  `"page"` `eslint-plugin-boundaries` exception (Sprint 5.1) — not moved
  to `src/components/`, avoiding an unforced change to Trading's
  already-shipped file structure.

### Bugs found and fixed during implementation

- **A real, pre-existing bug in Trading's `ProForm.tsx`** (Sprint 4.4,
  unrelated to Playbook's own contract): an untouched optional Select
  (Strategy/Session/Entry Trigger) submits an empty string rather than
  omitting the field, and the backend correctly rejects `""` as an
  invalid UUID (`422`) — confirmed independently via direct `curl`
  against `POST /trades` (`strategy_id: ""` → *"Input should be a valid
  UUID, invalid length: expected length 32... found 0"*). Discovered
  while first writing the "performance sourced from a real Trade" E2E
  fixture through the Trade Entry UI. **Not fixed** — modifying another
  module's already-shipped form is out of Sprint 7.2's scope (Playbook
  Frontend only); the E2E fixture instead creates and closes the Trade
  via direct API calls (`page.request.post`), the same "bypass the UI
  for fixture setup" precedent already used for catalog entries here and
  for Mistake tags in `mistakes.spec.ts`. Registered here for visibility,
  not silently worked around.
- **A stale `uvicorn` process from the Sprint 6.2 E2E session** was still
  bound to port 8000 (confirmed via `Get-NetTCPConnection`/`Get-Process`
  — started `2026-07-29 22:57`, well before Playbook's router existed),
  silently shadowing every fresh backend start this sprint and returning
  `404 Not Found` for every `/playbook-setups` request. Not a code
  defect — a leftover background process never killed in an earlier
  session's cleanup. Killed and replaced with a fresh process before any
  E2E test was trusted.
- Two E2E selector-strictness bugs, both caught by the first real test
  run: `getByRole(..., { name })` matches substrings case-insensitively
  by default, so `"Linked-<suffix>"` matched `"Unlinked-<suffix>"` too,
  and the bare `"Setup"` label matched a Bias-engine checklist field
  named `"Valid Setup"` — both fixed with `{ exact: true }`.

### Architecture

`features/playbook/{types,api,queryKeys,schemas}.ts` mirror Sprint 7.1's
backend contract field-for-field (re-verified directly against
`backend/app/modules/playbook/presentation/schemas.py`, not from
memory). `EditPlaybookSetupModal` always submits all four text fields
together, pre-filled via React Hook Form's `values` option so the form
stays synced to the setup's real current state — the same
"resend-the-full-current-or-edited-state" discipline `AmendTradeModal`
already applies to Trade, which is what actually guarantees an untouched
field can never be silently lost even though the backend's own `PATCH`
is genuinely partial. Every mutation (`create`/`update`/`deprecate`/
`add attachment`/`delete attachment`) invalidates both `playbookKeys.
list()` and `playbookKeys.detail(id)` where applicable, mirroring
`AmendTradeModal`'s own dual-invalidation pattern. `performance` is
rendered by `PerformanceCard` directly from the already-composed
`PlaybookSetupDetail.performance` object returned by `GET /playbook-
setups/{id}` — no client-side computation, no fallback value, no
formula, anywhere in this feature. Zero new dependency (`Recharts` not
needed — Playbook's own Key Components, per the Traceability Matrix, are
`DataTable, MetricCard` only).

### Added
- Frontend: `src/features/playbook/{types,api,queryKeys,schemas}.ts` (+
  `schemas.test.ts`, 4 unit tests); `components/{PerformanceCard,
  EditPlaybookSetupModal,AttachmentsCard,AddAttachmentModal}.tsx`;
  `pages/{PlaybookListPage,PlaybookSetupDetailPage}.tsx` (the latter
  replaces the Sprint-0-era `PlaybookPage.tsx` placeholder, now
  deleted). `router.tsx` — `/playbook` repointed, `/playbook/:setupId`
  added. `e2e/playbook.spec.ts` (4 tests).

### Verification performed
- Frontend: `tsc -b --noEmit` — clean; `eslint .` — clean (boundaries
  rules respected, `CatalogPickerModal` cross-feature import allowed only
  via the `"page"` exception); `vitest run` — **77 passed** (4 new; 73
  carried over); `vite build` — succeeds (Playbook adds no dependency
  heavy enough to need lazy-loading, unlike Statistics/Recharts).
- E2E: real stack (Docker Postgres 16 + `uvicorn` + Chromium/Playwright,
  never mocked) — `e2e/playbook.spec.ts` 4/4, stable across 3 repeated
  runs. Full suite: **25/25 passed**; one pre-existing, unrelated
  debounce-timing flake in `evaluation-preview.spec.ts` under parallel
  load, confirmed passing cleanly 4/4 in isolation — same category of
  flake already documented in Sprint 6.2's closing report, not a
  regression introduced here.
- Backend: no backend files changed this sprint; full backend `pytest`
  suite not re-run (no shared code touched — only the already-frozen
  Playbook/Statistics contracts were *read*, never modified).
- Audit: zero TODO/FIXME, zero `console.log`/debug statements in any new
  or modified file; `git status` confirms the diff surface is exactly
  the Playbook feature + `router.tsx` — no Trading file touched despite
  the bug found in `ProForm.tsx`.

### Confirmation
No `git push` was run at any point.

## Trade Entry Redesign v2.0 — Status/Result Split, Planned Trades, Take Profit, Margin Used

Not a Master Plan sprint — a user-requested redesign of the Trade domain
model and creation flow, approved through a four-turn review cycle: (1)
an initial request was **stopped** because it contradicted the frozen
Domain Model (no `Planned` state existed; `result` had no room for a
third "not yet traded" state; Sprint 4.1 had explicitly decided
`scoring_profile` must always be required); (2) the user redirected the
analysis to use `legacy/Trading Journal v2.0 Stable.xlsx`'s `📒 Trades
simple`/`📒 Trades` sheets as the literal source of truth, inspected
directly via `openpyxl` (cell values, data validations, formula vs.
manual-input cells) rather than assumption — this upgraded the original
request from "contradicts the frozen model" to "reveals a genuine gap
the frozen model never captured": both sheets really do have a 3-state
`Estado` column (`No iniciado`/`Activo`/`Cerrado`), a real `TP` column,
and a `Margin` column distinct from Position Size; (3) the user approved
the Status/Result split, Take Profit, and Margin Used, while explicitly
**rejecting** storing `ROI %`/`P&L %` ("nunca almacenar información
derivable" — they must stay computed) and rejecting the endpoint name
`activate` in favor of `open`, matching the project's existing verb
pattern (`register`/`amend`/`close`/`reevaluate`); (4) final approval
given with the explicit, rare instruction to update the frozen
documentation first, in order (Domain Model → Database Design → API
Specification → Master Plan → CHANGELOG), and only then implement code —
followed exactly, including a full MAJOR version bump of the Domain
Model (§20's own mandated process: Traceability Appendix + Domain
Invariants + Business Constraints Registry all updated in the same
revision).

### Documentation (updated first, per explicit instruction)
- `docs/03_TRADEOS_DOMAIN_MODEL.md` v1.1 → **v2.0** (MAJOR — redefines
  `TradeResult`, introduces `TradeStatus`): new **KDD-07** (§6, full
  Excel-cited decision record); Trade entity (§8.1) rewritten — Owned
  Information, Lifecycle (`Planned → Open → Closed(TP|SL|BE)`),
  Invariants; §13.1 lifecycle diagram redrawn; **DI-13** (Planned never
  scored, never in Analytics) and **DI-14** (`roi_percent`/`pnl_percent`
  always computed, never stored) added to §14; **INV-TRADE-02** redefined
  and **INV-TRADE-04** added (Planned → Open only, never directly →
  Closed) in §15; §18 Traceability Appendix and §21 Document Control
  updated.
- `docs/05_TRADEOS_DATABASE_DESIGN.md` v1.1 → v1.2: §6.9 `trading.trades`
  rewritten — `status` column (new, `NOT NULL`, no default);
  `take_profit`/`margin_used` (new, nullable); `entry_price`/`stop_loss`/
  `entered_at` relaxed to nullable; `result` relaxed to nullable, values
  narrowed to `tp`/`sl`/`be` (`'open'` retired); `roi_percent`/
  `pnl_percent` explicitly *not* added (computed-only, DI-14); all four
  CHECK constraints rewritten (`ck_trades_status` new,
  `ck_trades_inv_trade_02_status_fields` redefined per status).
- `docs/06_TRADEOS_API_SPECIFICATION.md` v1.1 → v1.2: `POST /trades`
  rewritten (conditional-required fields per `status`); new §11.1.1
  `POST /trades/{id}/open` (full spec + flow diagram, mirroring §11.1's
  style); `POST /trades/{id}/close` now requires `realized_pnl`/
  `closed_at` in the body (previously server-computed/optional); `GET
  /trades` gains `?status=` filter, `result` no longer accepts `open`.
- `docs/09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` — reviewed, **no
  changes needed** (operates at an abstraction level this redesign
  doesn't touch: INV-TRADE-01/02 IDs remain valid, "Simple/Pro share one
  domain model" still holds).

### Backend — Added
- `backend/alembic/versions/0012_trade_status_result_split.py` — adds
  `status`/`take_profit`/`margin_used`; backfills `status` from the
  retired `result='open'` value, then clears it to `NULL`; relaxes
  `entry_price`/`stop_loss`/`entered_at`/`result` to nullable; rewrites
  all four CHECK constraints; `entered_at`'s index becomes partial
  (`WHERE entered_at IS NOT NULL`).
- `backend/app/modules/trading/application/open_trade.py` —
  `OpenTradeUseCase`, the `Planned → Open` transition. Runs Evaluation
  for the first time (identical flow to `RegisterTradeUseCase`'s own
  Evaluation branch, never duplicated), publishes `TradeOpened` then
  `TradeEvaluated`.
- `tests/trading/test_open_trade_flow.py` (12 new tests) — Planned
  registration needs no entry facts/scoring_profile; `evaluation`/
  `checklist_answers` are `null`/`{}` for a Planned Trade; `GET
  /trades/{id}/evaluation` on a Planned Trade is `404`, not `500`; `GET
  /trades?status=` filter; the full `open` transition (success, `409`
  not-planned, `422` stop-placement, `404`); Statistics fully ignores a
  Planned Trade.

### Backend — Modified
- `domain/trade.py` — `PLANNED`/`OPEN`/`CLOSED` status constants;
  `RESULTS` narrowed to `tp`/`sl`/`be`; `validate_status_fields` (renamed
  from `validate_close_requires_result_and_exit_price`) now branches on
  `status`, not `result`; `compute_r_multiple`/`mfe_r`/`mae_r` guard
  `None` `entry_price`/`stop_loss`; new `roi_percent`/`pnl_percent`
  properties (`realized_pnl / margin_used`, then `/ leverage`) — computed
  only, per DI-14; new `_parse_leverage_multiplier` (mirrors the Excel's
  own `VALUE(SUBSTITUTE(G2,"X",""))`).
- `infrastructure/models.py`, `repository.py` — new columns; nullable
  `entry_price`/`stop_loss`/`entered_at`/`result`; `list_all` gains a
  `status` filter; `list_all_facts_for_statistics` excludes
  `status='planned'` **at the query itself** (DI-13 — a Planned Trade
  never reaches Statistics' aggregation code at all, not filtered there).
- `application/register_trade.py` — skips the entire Evaluation branch
  (no `ChecklistSnapshot`/`EvaluationSnapshot`/`TradeEvaluated`) when
  `status='planned'`; `scoring_profile` required only once `status !=
  planned`; `closed_at`/`realized_pnl` now accepted directly from the
  request (no longer server-computed).
- `application/close_trade.py` — checks `status == OPEN` (not `result !=
  OPEN`, retired); requires `realized_pnl`/`closed_at` in the request.
- `application/amend_trade.py` — `take_profit`/`margin_used` added to
  `AMENDABLE_FIELDS`; `status` deliberately still not amendable
  (transitions only via `open`/`close`).
- `application/get_trade.py`, `get_trade_evaluation.py` — a missing
  Checklist/Evaluation Snapshot is a `RuntimeError` (data-integrity bug)
  only when `status != planned`; for a Planned Trade it's the correct,
  expected `None`/`404`.
- `statistics/domain/statistics_aggregation.py` — `f.result != "open"` →
  `f.result is not None` (numerically identical for every pre-v2.0
  Trade, correct for the new `None`-while-Open semantics).
- `presentation/schemas.py`, `router.py` — new `OpenTradeRequest` +
  `POST /trades/{id}/open`; `TradeResponse`/`TradeSummaryResponse` gain
  `status`/`take_profit`/`margin_used`/`roi_percent`/`pnl_percent`,
  nullable `entry_price`/`stop_loss`/`entered_at`/`result`/`evaluation`;
  `GET /trades` gains `?status=`; keyset pagination's cursor is only
  built from a non-`NULL` `entered_at` (a page ending on a Planned row
  simply stops rather than crash-encoding a `NULL` boundary — the one
  known, accepted limitation of mixing a nullable sort key into existing
  keyset pagination, not a full redesign of it).

### Frontend — Added
- `components/TradeTypeDialog.tsx` — the approved "Option 4" resolution
  for `scoring_profile` (relabeled "Trade Type" in the UI): rather than
  a permanently-visible required field or a silent default, this dialog
  pops up **only at submission time**, only if left empty, prompting for
  one before re-submitting. Deliberately not built on `ConfirmDialog`
  (reserved for irreversible-action confirmations) — built on the shared
  `Modal` primitive instead, like every other Trading dialog.
- `components/OpenTradeModal.tsx` — `POST /trades/{id}/open`'s UI,
  surfaced from `ActionBar` only while `status='planned'`.
- `e2e/trading.spec.ts` — 2 new tests: the full Planned → Open lifecycle
  (no Evaluation until opened; Amend/Open/Delete only, no Close/
  Re-evaluate while Planned; Evaluation appears immediately after
  opening), and the `TradeTypeDialog` just-in-time prompt end to end.

### Frontend — Modified
- `types.ts`, `schemas.ts`, `api.ts` — `TradeStatus`; `TradeResult`
  narrowed (`"open"` retired); nullable `entry_price`/`stop_loss`/
  `entered_at`/`result`/`evaluation`; new `take_profit`/`margin_used`/
  `roi_percent`/`pnl_percent`; `tradeEntrySchema`'s `superRefine` now
  branches on `status` exactly like the backend's
  `validate_status_fields` (required fields are shape-optional in Zod,
  made conditionally required only via `superRefine` — matching the
  backend's own "Pydantic validates shape, the domain validates the
  business rule" layering, never duplicated as a hard-required Zod
  field); new `buildOpenTradeSchema(direction)` factory (direction isn't
  part of the `open` request body, so INV-TRADE-01 re-validation needs it
  supplied externally).
- `SimpleForm.tsx` — full redesign: `status` Select drives dynamic field
  visibility (`Planned` shows only Market/Direction; `Open` adds Trade
  Type/Entry/Stop/Take Profit/Entry Date; `Closed` adds Exit Price/
  Result/Close Date/Realized P&L) — switching back to `Planned` clears
  the now-hidden fields rather than letting a stale value silently ride
  along in the submitted payload.
- `ProForm.tsx` — `exit_price`/`result`/`take_profit` moved into
  `SimpleForm` (no longer duplicated here); adds `margin_used`.
- `CloseTradeModal.tsx`, `AmendTradeModal.tsx` — `realized_pnl`/
  `closed_at` and `take_profit`/`margin_used` fields respectively.
- `ActionBar.tsx` — `Open` offered only while `status='planned'`; `Close`
  gated on `status='open'` (previously the now-retired `result==='open'`);
  `Re-evaluate` hidden while `status='planned'` (DI-13 — nothing to
  re-run yet).
- `TradeSummaryCard.tsx`, `EvaluationSummaryCard.tsx`,
  `TradesListPage.tsx`, `FilterBar.tsx` — status badges, nullable-field
  handling, a "still Planned, no Evaluation yet" empty state, `?status=`
  filter, `"open"` removed from the Result filter's options.

### Bugs found and fixed during implementation
- **Migration `0012`'s own backfill ran in the wrong order**: `UPDATE
  trading.trades SET result = NULL WHERE result = 'open'` was sequenced
  *before* `result`'s `NOT NULL` constraint was relaxed — violates that
  still-active constraint for every currently-open Trade. Caught
  immediately on the first real `alembic upgrade head` against the dev
  database (not by any test, since the test suite's schema is created
  fresh from the ORM models, never by replaying migrations against
  pre-existing data) — fixed by moving the three `alter_column(...,
  nullable=True)` calls before the backfill `UPDATE`s. Round-trip
  verified (`upgrade → downgrade → upgrade`) against the real dev
  database afterward.
- **A real frontend submission bug**, also caught only by driving the
  actual running stack, not by any of `tsc`/`eslint`/`vitest`: an
  untouched `<input type="date">` submits `""`, not `undefined` (RHF
  reads the DOM value directly) — `tradeEntrySchema`'s `entered_at`/
  `closed_at` therefore reached the backend as `""` even when correctly
  left blank for a Planned Trade, and Pydantic's `datetime` field rejects
  `""` ("too short") rather than treating it as absent. Registering a
  Planned Trade through the actual UI silently failed to navigate away
  from the still-open modal. Fixed with a `optionalDateString` Zod
  transform (`"" → undefined`) applied to both fields.
- Two E2E selector-strictness issues in the new Planned/Open test,
  caught on first run: `getByText("PLANNED")` matched both the status
  badge and the "still Planned" empty-state sentence (fixed with `{
  exact: true }` on the badge assertion); playwright-test-generated
  `.mjs` debug script needed `@playwright/test`'s bundled `chromium`
  import, not the unlisted `playwright` package.

### Verification performed
- Backend: `pytest` — **352 passed** (38 pre-existing tests updated for
  the new required `status` field/nullable core facts, 12 new); `ruff
  format --check` / `ruff check` — clean; `mypy app` — clean, 195 source
  files.
- Frontend: `tsc -b --noEmit` — clean; `eslint .` — clean; `vitest run` —
  **88 passed** (20 in `schemas.test.ts`, 6 in an updated
  `TradeSummaryCard.test.tsx`); `vite build` — succeeds.
- Migration: applied to the real dev database (Docker Postgres 16, not
  the test suite's fresh-from-ORM schema) — `upgrade head` succeeded
  after the ordering fix above; `downgrade -1` → `upgrade head` round
  trip verified clean.
- E2E: real stack (Docker Postgres 16 + `uvicorn --reload` + `vite dev`,
  both already running under a session this agent could not terminate —
  confirmed via a direct `curl` probe that both had already hot-reloaded
  every backend/frontend change before any E2E test ran, rather than
  assumed). `e2e/trading.spec.ts` — 5/5, including both new Planned/Open
  and `TradeTypeDialog` tests. Four other spec files
  (`journal`/`mistakes`/`playbook`/`statistics`) had their own
  trade-creation fixtures on the old payload shape — updated identically.
  Full suite: **26/27 passed**; the one failure
  (`evaluation-preview.spec.ts`, unrelated to Trading, a debounce-timing
  assertion) reproduces only under parallel-worker load and passed
  cleanly 4/4 in isolation — the same class of pre-existing flake already
  documented in Sprint 6.2/7.2's closing reports, not a regression.

### Deferred (explicitly, by the user)
- The 4-bucket Pro Mode Excel audit (Ya existen / Faltan en Simple /
  Faltan en Pro / No deberían existir) and any resulting Pro Mode field
  expansion — required before touching Pro Mode further, not part of
  this redesign.
- Dashboard's future Open/Planned/Closed trade-count breakdown — a
  documented future Phase 8 concern (API Specification/Domain Model note
  it as supportable), no implementation here.

### Confirmation
No `git push` was run at any point.

## Sprint 8.1 — Dashboard Composition

Phase 8 of the Implementation Master Plan, closing sprint — Milestone M8
is achieved. Scope (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9):
*"`GET /dashboard`, composing already-built Trades + Statistics
capability; the Dashboard page... introduces no new backend logic."*
Verified as the correct next sprint by cross-checking the Master Plan's
own sequencing against `CHANGELOG.md`'s last Master Plan entry (Sprint
7.2) and the real code (`GET /dashboard` did not exist; `DashboardPage`
was still Sprint 0.3's placeholder) before writing anything — no
contradiction found between the Master Plan, the API Specification, and
the Frontend Blueprint for this sprint.

### Pre-analysis: two undocumented numeric values, resolved with the
product owner before implementation
No frozen document names a numeric default for either value; both were
confirmed explicitly rather than invented:
- **Rolling window default** for the composed response: **10**, matching
  the only real precedent in this codebase — `RollingTab.tsx`'s own
  `useState<RollingWindow>(10)`.
- **Recent Trades preview size**: **5**, one order of magnitude with the
  Frontend Blueprint's own explicit "top 3" for the Mistakes preview.

### Architectural decisions (adjusted from the initial plan, per product
owner review)
- **`ListTradesWithEvaluationsUseCase`** added to Trading's own
  Application layer (`trading/application/list_trades_with_evaluations.py`,
  purely additive — `GET /trades`'s existing router is untouched) so
  Dashboard can obtain Trade+current-Evaluation pairs without ever
  reaching into Trading's `infrastructure/` directly, the same
  cross-module precedent `ListTradeStatisticsFactsUseCase` (Sprint 6.1)
  and `ListMistakeOccurrencesUseCase` (Sprint 5.2) already established.
- **Own DTOs, not shared ones.** A real tension surfaced mid-implementation:
  the product owner's instruction to "reuse Trading's read models to
  avoid drift" collided with `playbook/presentation/schemas.py`'s own,
  already-shipped docstring — *"each module owns its own HTTP contract
  DTOs (no cross-module presentation-layer import)... applied everywhere
  in this project."* Flagged and resolved before writing code: Dashboard
  reuses the Application-layer objects where the actual computation
  lives (`Trade`, `StatisticsSummary`, `RollingStatistics`,
  `MistakeRankingResult` — zero risk of a second, drifting formula), but
  defines its own lightweight Pydantic/TypeScript response shapes
  (`Dashboard*Response` / `Dashboard*` types), exactly mirroring how
  `PlaybookSetupPerformanceResponse` already duplicates
  `StatisticsSummaryResponse`'s fields rather than importing them
  (Sprint 7.1). Confirmed machine-enforced on the frontend by this
  project's own `eslint-plugin-boundaries` config: only `pages/*` may
  import across features; `dashboard/{api,types,queryKeys,components}`
  never import from `trading`/`statistics`/`mistakes`.
- **Single `build_get_dashboard_use_case(session)` factory**
  (`dashboard/application/get_dashboard.py`) — the router calls exactly
  one factory and invokes it; it never constructs
  `GetStatisticsOverviewUseCase`/`GetRollingStatisticsUseCase`/
  `GetMistakeRankingUseCase`/`ListTradesWithEvaluationsUseCase` itself,
  matching every other module's `build_*` discipline.
- **Extensibility, deliberately minimal.** `DashboardSummary` holds one
  field per composed section, each resolved by its own independent call
  in `execute()`. A future composed section (Equity Curve, Playbook
  Performance, Market Bias — all currently unbuilt/reserved per
  `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §17) means adding one field and
  one call, never restructuring existing ones. No registry, no plugin
  mechanism — none of those sections has a confirmed endpoint today, so
  none is stubbed.
- No `domain/` or `infrastructure/` folder for the new `dashboard/`
  module — Dashboard is explicitly not a Bounded Context
  (`TRADEOS_API_SPECIFICATION.md` §5.1) and owns no data, mirroring the
  same "no infrastructure for a pure composition" precedent Statistics
  and Mistakes already set.

### Bug found during E2E verification — pre-existing, unrelated,
not fixed
While writing the "log a real Trade, see it on the Dashboard" E2E test,
`POST /api/v1/trades` returned `422 Unprocessable Entity` when submitted
through `TradeEntryModal`'s current UI flow, confirmed via the real
backend's own structured request log. This is **not a Dashboard defect**
— the identical, unmodified helper in the already-existing (uncommitted)
`e2e/statistics.spec.ts` fails at the exact same line with the exact
same error, proving the regression lives in the still-uncommitted Trade
Entry Redesign v2.0 work, not in anything built this sprint. **Not
fixed** — out of Sprint 8.1's scope (Dashboard composition only), and
modifying another module's unreviewed, uncommitted form code risks
masking or misdiagnosing a defect that isn't this sprint's to own.
Registered here for visibility, matching the same "found, not silently
worked around" posture Sprint 7.2's own `ProForm.tsx` bug note set.
Backend correctness was verified instead through Sprint 8.1's own
integration tests, which register/close Trades directly via the API
(`httpx.AsyncClient`, bypassing the affected UI form entirely) and pass
cleanly.

**Correction (post-Sprint-8.1 investigation, see the hotfix entry
below):** the attribution above — "the regression lives in the still-
uncommitted Trade Entry Redesign v2.0 work" — is **factually incorrect**
and is corrected here rather than silently edited. A full root-cause
investigation (requested before proceeding to Phase 9) found via
`git log --follow -S"No configuration version is available to evaluate
against" -- backend/app/modules/trading/application/register_trade.py`
that this exact validation was introduced by commit `3991112`, Sprint
4.1's original `POST /trades` implementation — four sprints before Trade
Entry Redesign v2.0 existed. The 422 is `RegisterTradeUseCase` correctly
enforcing System Architecture ADR-03 (a Trade cannot be evaluated
without a published `ScoringConfigurationVersion`) against a database
with zero rows in `configuration.scoring_configuration_versions` — an
environment/bootstrap gap (nothing had run `scripts/seed_configuration.py`
on that machine), not a code defect in any layer, and not something v2.0
introduced or touched. See "Hotfix — Environment Bootstrap & E2E Test
Isolation" below for the full analysis and the fix.

### Added
- Backend: `app/modules/trading/application/list_trades_with_evaluations.py`
  (new, additive); `app/modules/dashboard/{application/get_dashboard.py,
  presentation/{router.py,schemas.py}}`; `main.py` registers
  `dashboard_router`. `tests/dashboard/test_dashboard_flow.py` (5
  integration tests, including the Master Plan §10-named regression
  test: "Dashboard never duplicates a number differently than its source
  endpoint returns it").
- Frontend: `src/features/dashboard/{types,api,queryKeys,format}.ts`,
  `components/{RecentTradesPreview,TopMistakesPreview}.tsx` (+ 5 unit
  tests), `pages/DashboardPage.tsx` (replaces the Sprint-0-era
  placeholder). `e2e/dashboard.spec.ts` (3 tests).

### Verification performed
- Backend: full `pytest` suite — **357 passed** (5 new; 352 carried
  over), real ephemeral PostgreSQL 16 via Testcontainers, never mocked;
  `ruff check` — clean; `mypy` — clean (0 issues, 7 source files).
- Frontend: `tsc -b --noEmit` — clean; `eslint .` — clean (`boundaries`
  rules respected: no non-page file in `features/dashboard` imports
  another feature); `prettier --check` on the two new files — clean (a
  pre-existing formatting debt across ~24 unrelated, already-uncommitted
  files was left untouched — out of this sprint's scope); `vitest run`
  — **93 passed** (5 new; 88 carried over).
- E2E: real stack (Docker Postgres 16 + `uvicorn` + Chromium/Playwright,
  never mocked) — `e2e/dashboard.spec.ts` **2/3 passed** (empty-state
  landing page, unauthenticated redirect); the third (full log-a-Trade
  walkthrough) is blocked by the pre-existing, unrelated bug documented
  above, reproduced identically against the already-existing
  `statistics.spec.ts` to confirm it is not a regression introduced this
  sprint.
- Audit: zero TODO/FIXME, zero `console.log`/`debugger` statements in
  any new file (`grep` across every backend and frontend path touched
  this sprint — no matches).

### Confirmation
No `git push` was run at any point.

## Hotfix — Environment Bootstrap & E2E Test Isolation (post-Sprint 8.1, pre-Phase 9)

Closes the one pending item carried over from Sprint 8.1's closing report:
the `POST /trades` 422 that blocked the Dashboard E2E's full walkthrough.
A full technical investigation (requested and delivered separately,
before any file was touched) established the root cause and is
summarized here; see the correction note added to Sprint 8.1's own "Bug
found during E2E verification" section above for the retraction of that
sprint's incorrect attribution.

### Root cause

Not a code defect. `RegisterTradeUseCase`/`OpenTradeUseCase`/
`PreviewEvaluationUseCase` correctly require a published
`ScoringConfigurationVersion` to evaluate against
(`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03) — this business rule dates to
Sprint 4.1 (commit `3991112`), unchanged since. `scripts/seed_
configuration.py`, the script that publishes the first version, is a
manual, one-time, per-environment bootstrap step
(`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Sprint 2.1: "Dependencies: Phase
1 (a `user_id` must exist to attribute the seed action)" — this is why it
cannot run as part of a schema migration, which executes before any user
exists). On a freshly cloned/migrated environment nobody had run it, and
nothing surfaced that gap until the first `POST /trades` — reproduced
identically via direct `curl` against the backend with zero frontend
involvement, confirming it as a pure backend/database-state condition,
not a frontend/backend contract issue.

A second, related gap: `e2e/trading.spec.ts`'s own comment claimed "no
Configuration setup needed... seeded by migration `0004`" — false;
migration `0004` seeds `engine_types`/`scoring_profiles` reference data
only, never a published `ScoringConfigurationVersion` (its own docstring
already said as much: those two tables "[have] no `user_id` attribution
requirement, unlike the first `ScoringConfigurationVersion`"). The suite
only ever passed because `evaluation-preview.spec.ts` and
`configuration-and-catalogs.spec.ts` each publish their own Configuration
as part of their own setup, and Playwright's `fullyParallel` execution
against one shared, non-reset local Postgres let that publish silently
satisfy every other spec's unstated dependency — a hidden ordering
coupling, not a real fix.

### Decision: bootstrap strategy (Option B of three evaluated)

Three alternatives were compared against this project's own principles
(Clean Architecture layering, minimal maintenance surface, no invented
business rules):

- **Keep the manual script, documented only.** Rejected as insufficient
  — it is exactly the step that was already forgotten once; it does
  nothing to make a new environment self-describing.
- **A single official bootstrap command** (chosen) — `backend/scripts/
  bootstrap.py`, living beside `seed_configuration.py` in the same
  "tooling outside `app/modules/`" category the Sprint 2.1 CHANGELOG
  entry already established for that script. Orchestrates `alembic
  upgrade head` (Stage 1, no prior state required) then delegates to
  `seed_configuration.seed()` unchanged (Stage 2, once a `--user-id` is
  known) — zero duplicated logic, zero new business rule.
- **Bootstrap from the FastAPI `lifespan` hook.** Rejected. `main.py`'s
  `lifespan` today does pure in-memory wiring (binding the event
  dispatcher) with no persistent side effect and no notion of "current
  user" — publishing a Configuration there would need to invent a
  `user_id` from nothing, breaking the Master Plan's own attribution
  requirement, and would re-run once per worker process on every
  multi-worker deployment, an automatic, repeated invocation of business
  logic no other part of this codebase's startup path performs.

No change was made to `RegisterTradeUseCase`, the Domain Model, any API
contract, or any validation rule — confirmed by `git diff --stat`
against `backend/app/modules/trading/` and `backend/app/modules/
configuration/domain/` and `.../application/` showing zero changes.

### Added
- `backend/scripts/bootstrap.py` — new, additive. Two-stage CLI
  (`--user-id` optional): Stage 1 runs `alembic upgrade head`
  programmatically (`alembic.command.upgrade`); Stage 2, once a
  `--user-id` is supplied, calls the existing, unmodified `scripts.
  seed_configuration.seed()`. Idempotent in both stages (Alembic tracks
  applied revisions; `seed()` already no-ops once a published version
  exists).
- `README.md` — new. The project's first installation runbook: 
  prerequisites, backend/frontend setup, the two-stage bootstrap with
  the exact commands, and a golden-path checklist (register → log in →
  create a Trade → Evaluation → Dashboard) to confirm a clean environment
  is fully operational without any undocumented manual step.
- `frontend/e2e/helpers/configuration.ts` — new. `ensurePublishedConfiguration(page)`
  publishes a fresh, empty `ScoringConfigurationVersion` via direct API
  calls (no criteria/weights — the specs using it never assert on score
  values, only end-to-end completion and price-derived metrics).
  Publishing itself is protected against data corruption by
  `ScoringConfigurationVersionRepository.lock_for_publish()`'s advisory
  lock plus migration `0006`'s partial unique index (`ADR_CONFIGURATION
  _PUBLISH_RACE_CONDITION.md`, already closed) — but that guarantees only
  "at most one published row, ever," not "the specific version a given
  test just published stays published for the rest of that test." See
  the `playwright.config.ts` change below for why that distinction
  mattered here.

### Modified
- `frontend/e2e/trading.spec.ts`, `statistics.spec.ts`, `dashboard.spec.ts`,
  `journal.spec.ts`, `mistakes.spec.ts` — each `registerAndLogIn` now
  calls `ensurePublishedConfiguration` after logging in. All five create
  or close a Trade via the UI (directly, or through the shared
  `createAndCloseTrade`/`createTradeSimple` helpers) and were equally
  exposed to the same hidden cross-file dependency; `evaluation-preview
  .spec.ts` and `configuration-and-catalogs.spec.ts` already published
  their own Configuration and needed no change. `playbook.spec.ts` never
  creates a Trade and was unaffected.
- `frontend/e2e/trading.spec.ts` — corrected the stale comment
  attributing "no Configuration setup needed" to migration `0004`;
  replaced with the accurate reason (this suite now publishes its own).
- `frontend/e2e/dashboard.spec.ts` — two locator fixes in the "Dashboard
  composes metrics..." test, found only once this hotfix let the test
  run past the 422 for the first time since Sprint 8.1: `getByText("Win
  Rate")` and `getByText("100.0%")` were ambiguous (the Rolling/All-Time
  section below renders its own "Rolling Win Rate"/"All-Time Win Rate"
  cards, and with one Trade all three percentages read identically) —
  scoped to the specific MetricCard via its exact label and that label's
  DOM sibling. Pre-existing, dormant since Sprint 8.1 (never previously
  reachable — the 422 always blocked the test first); not a regression
  from this change, but only discoverable because of it.
- `frontend/playwright.config.ts` — added `workers: 1`. Root cause: five
  more spec files now each publish their own `ScoringConfigurationVersion`
  (above), and Playwright's `fullyParallel` execution runs different spec
  files in separate, concurrent workers against the same shared database.
  A publish from any worker immediately supersedes whichever version
  another worker's test was relying on, mid-test — this is the exact,
  already-documented 2-file race between `evaluation-preview.spec.ts` and
  `configuration-and-catalogs.spec.ts` (`ADR_CONFIGURATION_PUBLISH_RACE
  _CONDITION.md`; tolerated across Sprints 6.2/7.2/Trade Entry v2.0's own
  closing reports as an occasional, re-run-and-confirm flake), just with
  5 more files now able to trigger it. Empirically, with 6 default
  workers this reproduced as a deterministic-feeling failure (`evaluation
  -preview.spec.ts`'s score assertions reading a stray empty Configuration
  published by a concurrently-running file), not the occasional flake it
  used to be — widening the blast radius this much made "re-run and
  confirm it's a flake" no longer an honest verification story. `workers:
  1` removes cross-file concurrency structurally (the same "database
  constraint over caller discipline" preference this project's backend
  fix already made for the identical underlying resource), fully closing
  this class of flake rather than just not making it worse. Trade-off:
  full suite wall-clock time rose from ~20s (6 workers) to ~67s (1
  worker) — judged acceptable for a single-maintainer project with no CI
  pipeline yet; revisit if that changes.
- `CHANGELOG.md` — added the correction note to Sprint 8.1's "Bug found
  during E2E verification" section (see above).

### Verification performed
- Backend: `pytest` (full suite) — **357 passed**, 0 failed, real
  ephemeral PostgreSQL 16 via Testcontainers; `ruff format --check` /
  `ruff check` — clean (one pre-existing formatting debt in
  `tests/dashboard/test_dashboard_flow.py`, already present in Sprint
  8.1's own commit `45cc28b`, left untouched — out of scope, same
  precedent Sprint 8.1 itself set for unrelated formatting debt); `mypy`
  — 9 pre-existing errors in 4 files (`test_statistics_aggregation.py`,
  `test_correlation_id_middleware.py`, `test_jwt.py`, an unchecked-defs
  note in `test_seed_bias_engine.py`), none in any file this hotfix
  touched — confirmed via `git log` that none of the 4 were modified
  here. No test needed changing — the fix is additive tooling, not a
  behavior change to any Use Case.
- Frontend: `tsc -b --noEmit` — clean; `eslint .` — clean; `vitest run`
  — **93 passed**, 0 failed; `prettier --check` on every touched file —
  clean.
- E2E: full `playwright test` suite (30 tests) run against a **completely
  fresh** environment from this session's own clean-install verification
  below (not a pre-warmed dev database) — **30/30 passed**, confirmed on
  two consecutive full runs after the `workers: 1` fix (deterministic,
  not "passed once"). Before that fix, the full suite intermittently
  failed 1-2 of `evaluation-preview.spec.ts`/`configuration-and-catalogs
  .spec.ts` (the pre-existing cross-file Configuration race, confirmed
  via isolated re-runs of just those files passing cleanly every time) —
  root-caused to this hotfix's own new publishers, not a flake to shrug
  off, and fixed structurally rather than re-run-until-green.
- Clean-install verification, exactly following the new `README.md`,
  performed once end-to-end this session: `docker compose down -v` (drop
  the Postgres volume entirely) → `docker compose up -d` → `PYTHONPATH=.
  poetry run python scripts/bootstrap.py` (Stage 1, zero prior state) →
  registered a user via `POST /api/v1/auth/register` → confirmed `POST
  /trades` still 422s at this point (proving the bug reproduces on a
  genuinely fresh install, not just this developer's already-seeded
  machine) → `PYTHONPATH=. poetry run python scripts/bootstrap.py
  --user-id <uuid>` (Stage 2) → re-sent the identical `POST /trades`
  payload → **201 Created** with a full Evaluation body, confirming the
  fix directly against the backend, independent of the E2E suite → full
  `playwright test` suite (register → log in → create a Trade → close it
  → view its Evaluation → `/dashboard` renders metrics and the Recent
  Trades preview, per `trading.spec.ts`'s and `dashboard.spec.ts`'s own
  golden-path tests) — 30/30 passed against this same freshly-bootstrapped
  stack, serving as the browser-driven walkthrough.
- Audit: `grep` confirms zero TODO/FIXME/`console.log`/`debugger` in
  every file touched; `git diff --stat` confirms no change under
  `backend/app/modules/trading/domain/`, `.../application/register_trade.py`,
  `backend/app/modules/configuration/domain/`, or any `*/presentation/schemas.py`
  (API contracts unchanged).

### Confirmation
No `git push` was run at any point.

## Sprint 9.1 — Containerization & Managed Database

Phase 9 (Deployment & Production Hardening), first sprint
(`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9). Preceded by a full
Fase 1–3 review cycle: audited all nine canonical documents plus every
prior ADR to determine the next real sprint (not assumed from this
CHANGELOG); found and resolved two genuine, previously-unresolved
blocking items before any code was written — **OQ-3** (Product Bible
Open Question 5, "does the Excel migrate?") — resolved: the Excel
remains a permanent historical record, no import sprint added to Phase
4 — and **OQ-1** (health-check contract, Backend Blueprint BE-7) —
resolved via `TRADEOS_API_SPECIFICATION.md` v1.3 (see that document's
own Document Control table for the full amendment). This sprint covers
only what was explicitly approved as in-scope: the Dockerfile, its own
isolated validation compose stack, and the migrations/seeding split.
**Explicitly not in scope, not attempted:** choosing a real hosting
platform or managed PostgreSQL provider, TLS, secrets management
(Sprint 9.3) — Milestone M9 is not claimed here.

### Decision: separating migrations from Configuration seeding

Previously, `scripts/bootstrap.py` was a single two-stage script mixing
both concerns. Per explicit instruction, migrations and seeding are now
structurally independent commands with independent lifecycles:

- `backend/scripts/migrate.py` (new) — the *only* thing it does is
  `alembic upgrade head`. No dependency on any user existing. This is
  what a real deployment runs — safe to invoke unconditionally, once,
  before the application ever serves a request.
- `backend/scripts/seed_configuration.py` — unchanged. Still requires
  `--user-id`, still a manual, one-time, per-environment step.
- `backend/scripts/bootstrap.py` — narrowed to what it always should
  have been described as: a **local-development convenience wrapper**
  that composes the two scripts above for a developer who doesn't want
  to remember two commands. Its own docstring now says so explicitly.
  Its public CLI (`--user-id` optional, two-stage usage) is unchanged;
  internally it now imports `run_migrations` from `scripts/migrate.py`
  instead of defining its own copy — zero duplicated logic.

### Decision: `GET /healthz` (per `TRADEOS_API_SPECIFICATION.md` v1.3, §6.0)

Added to `backend/app/main.py`: liveness only, no dependency checks,
outside `/api/v1`, exempt from `AuthenticationMiddleware` via the same
`PUBLIC_PATHS` mechanism already used for the three unauthenticated
`/auth/*` endpoints. Deliberately minimal (`{"status": "ok"}`) and
deliberately not expanded with a `/readyz` this sprint — see the API
Specification's own §6.0 for the full contract-stability commitment.

### Added
- `backend/scripts/migrate.py` — migrations only (see above).
- `backend/Dockerfile` — `python:3.12-slim`, Poetry, `--only main
  --no-root` (no dev/test dependencies ship), non-root `appuser`, no
  `--reload`, a `HEALTHCHECK` hitting `GET /healthz` via Python's own
  `urllib` (no `curl` added, keeping the image lean), `ENV
  PYTHONPATH=/app` (see "Bug found and fixed" below for why).
- `backend/.dockerignore` — excludes `.venv`, caches, `.env`, `tests/`,
  both compose files from the build context.
- `backend/docker-compose.container.yml` — an **isolated** stack for
  validating the Dockerfile's own image: its own Postgres (no volume,
  throwaway by design), backend exposed on host port `8080` (not `8000`,
  to coexist with a local dev session), explicit `name:
  tradeos-container-validation` project name. Does **not** touch
  `docker-compose.yml`, the development environment, at all.

### Modified
- `backend/scripts/bootstrap.py` — see "Decision" above; behavior
  unchanged, internals de-duplicated.
- `backend/app/main.py` — registers `GET /healthz`; adds `/healthz` to
  `PUBLIC_PATHS`.
- `docs/06_TRADEOS_API_SPECIFICATION.md` v1.2 → v1.3 — see that
  document's own Document Control table.

### Bug found and fixed during this sprint's own validation (not anticipated in the plan)

**Near-miss with the local dev database.** The first version of
`docker-compose.container.yml` had no explicit `name:`. Docker Compose
derives its project name from the current directory by default, which
is `backend` for **both** compose files — without an explicit,
distinct name, `docker compose -f docker-compose.container.yml up`
resolved its `postgres` service to the exact same container name
(`backend-postgres-1`) as the dev compose's, and — because this file's
`postgres` service intentionally has no volume — silently recreated and
replaced the running dev Postgres container with a throwaway, unmounted
one. Caught immediately (the dev container's absence was visible in
`docker ps` right after), and the named volume `backend_tradeos_postgres_data`
was confirmed untouched on disk (`docker volume ls`) — a plain `down`
never deletes a named volume, only `down -v` does, and that was never
run against it. The dev container was restored cleanly via `docker
compose up -d` (dev's `docker-compose.yml`), reattaching to the same
volume with zero data loss. Fixed structurally, not just noted: `name:
tradeos-container-validation` added to the top of the file, with the
full incident documented inline as a comment, so this cannot recur
silently. Registered here per this project's own standing rule (Master
Plan §11.1, item 8: "any new Known Gap or Open Question discovered
during the phase is registered, never silently patched") even though
this is a tooling incident rather than a Known Gap in the formal sense.

**`ModuleNotFoundError: No module named 'app'` running `seed_configuration.py`
inside the container.** `python scripts/x.py` puts only the script's own
directory on `sys.path`, not the working directory — exactly why local
development docs already require `PYTHONPATH=.`. `uvicorn app.main:app`
(the image's own `CMD`) resolves correctly through its own import
machinery and never hit this; any future ad hoc `docker exec <image>
python scripts/...` call would have, repeatedly. Fixed once, at the
image level (`ENV PYTHONPATH=/app` in the `Dockerfile`), rather than
requiring every future caller to remember the flag.

### Verification performed

- **Backend regression:** full `pytest` suite, unchanged — **357
  passed**, 0 failed. `ruff check`/`ruff format --check` — clean (the
  same one pre-existing, unrelated formatting debt in
  `tests/dashboard/test_dashboard_flow.py` from Sprint 8.1's own commit,
  still untouched). `mypy` — same 9 pre-existing, unrelated errors in
  the same 4 files as every prior sprint's own verification section;
  none in any file this sprint touched.
- **Image build:** `docker build` — succeeds without any additional
  system packages (asyncpg/argon2-cffi/cryptography all resolved
  prebuilt wheels; no `gcc`/`libpq-dev` needed). **Cold build (base
  image pull included): ~218s. Warm rebuild (dependency layer cached,
  only a small `ENV` change): ~1.5s** — confirms Docker layer caching
  behaves as expected for this Dockerfile's own layer ordering
  (dependencies installed before application code is copied).
- **Image size:** **498 MB.**
- **Container startup:** from `docker compose up -d` being issued to
  the backend container reporting `healthy` (Postgres startup + backend
  boot + first passing `HEALTHCHECK`): **~11.8s** (measured twice for
  consistency after the `name:` fix).
- **`HEALTHCHECK`:** passes — `docker inspect`'s own health log shows
  `"Status": "healthy"`, `"ExitCode": 0`. External check via the mapped
  port: `curl http://localhost:8080/healthz` → `{"status":"ok"}`,
  `HTTP 200`.
- **Migrations inside the container:** `docker compose exec backend
  python scripts/migrate.py` — all 12 migrations (`0001`→`0012`) applied
  cleanly, in order, against the isolated stack's fresh Postgres.
- **Full smoke test against the running container** (real `CMD`, no
  `--reload`, exposed on `8080`), following the exact five-step flow
  approved for this sprint (infra → migrate → app up → register user →
  seed once): register → login → `POST /trades` **pre-seed, confirmed
  422** (identical to every prior confirmation this project has done of
  this exact precondition) → `docker exec ... python
  scripts/seed_configuration.py --user-id <uuid>` → `POST /trades`
  **201**, full Evaluation body returned. Proves the migrate/seed
  separation works end-to-end inside the actual container, not just in
  local dev.
- **Dev environment integrity:** confirmed `backend-postgres-1` (the
  development Postgres) was running, on its original volume, throughout
  and after every container-validation run in this sprint.

### Confirmation

This sprint is **not** a claim that Phase 9 or Milestone M9 is complete.
Explicitly documented, per instruction: validation in this sprint was
performed **entirely against local Docker** (the isolated
`docker-compose.container.yml` stack) — no managed PostgreSQL instance
and no real hosting platform were used, because none has been chosen
yet. The final verification against a real managed database, on the
eventually-chosen hosting platform, remains pending and is what will
actually permit declaring the deployment portion of the roadmap
finished — this sprint closes the containerization and bootstrap-
separation work, not the deployment itself. No `git push` was run at
any point.

## Sprint 9.2 — Frontend Static Hosting & TLS (Render)

Phase 9 (Deployment & Production Hardening), second sprint
(`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9). Preceded by a full Fase
1-3 review cycle (documentary audit, contradiction check, Technical
Plan) plus three independent, adversarial technical-review rounds on
the Plan Técnico before implementation began — a heavier gate than any
prior sprint, reflecting that this is the first sprint committing to a
real, paid, external hosting provider (Render) rather than local-only
validation.

### Decision: Render, chosen from the class already named in frozen docs

`TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1 and `TRADEOS_TECHNICAL_STACK.md`
§13 deliberately commit only to a *class* of managed platform
("Railway/Fly.io/Render-equivalent"), never a vendor. Render was
selected (user decision) because one provider covers all three pieces
TradeOS needs — Docker web service, managed PostgreSQL, and a static
site with SPA-rewrite support — with automatic, free TLS on every
service. This sprint's `render.yaml` targets the `basic-256mb` Postgres
plan and the `starter` web-service plan specifically because Render's
free tiers were disqualified for concrete, cited reasons: free web
services spin down after 15 minutes of inactivity, and free Postgres
instances are automatically deleted after a fixed trial period —
unacceptable for a database that becomes the user's permanent trading
journal. Approximate cost: $7/mo (web service) + $6/mo (Postgres) ≈
$13/mo; the Static Site itself carries no separate plan cost.

**No real Render deployment was performed in this sprint** — no Render
account/credentials are available in this environment. `render.yaml`
is complete, IaC-correct Blueprint configuration, verified against
Render's own official documentation (not memory) for every field used.
Everything verifiable without an actual Render account was verified
empirically, described below. Actually applying this Blueprint to a
live Render account, and the resulting real-infrastructure smoke test,
remain the user's own next manual step.

### Decision: `/healthz` stays liveness-only; `/readyz` explicitly deferred

Render's `healthCheckPath` gates traffic cutover during zero-downtime
deploys — a *readiness* concern. The Technical Plan initially proposed
introducing `GET /readyz` (checking real PostgreSQL connectivity) to
close that gap, which a review round correctly flagged as a scope
change relative to Sprint 9.1's explicit, approved contract ("`/healthz`
= liveness, no readiness yet"). Resolved by explicit architectural
decision, not by silent omission: `healthCheckPath: /healthz` is kept
for this sprint; `/readyz` is deferred to a future sprint. The residual
risk — an instance with broken database connectivity would still pass
`/healthz` and receive real traffic — is accepted explicitly, justified
by `TRADEOS_PRODUCT_BIBLE.md` NFR 10.4 (single-user, modest availability)
and by Architectural Principle 4 (don't build infrastructure ahead of a
demonstrated need). `/healthz`'s contract (`docs/06...md` §6.0) is
completely unchanged — this sprint adds no new endpoint.

### Decision: the Dockerfile from Sprint 9.1 is untouched

Rendering the dynamic `$PORT` Render assigns required *some* mechanism
to substitute an environment variable into the startup command — but
Docker's exec-form `CMD` (`["uvicorn", ...]`, already approved in 9.1)
performs no shell substitution at all. The first fix considered was
changing the Dockerfile's own `CMD` to a shell form; a review round
correctly rejected this because a bare `sh -c "uvicorn ..."` demotes
uvicorn from PID 1 to a child of the shell — `docker stop` (and
Render's own instance-recycling on every deploy) sends `SIGTERM` to
PID 1, and `dash`/`sh` on `python:3.12-slim` does not forward it to
children by default, so uvicorn would never receive it and get hard-
killed by `SIGKILL` after the grace period, dropping in-flight
requests on every single deploy. Resolved by keeping the Dockerfile's
`CMD` completely unmodified and instead declaring, in `render.yaml`
only:

    dockerCommand: sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'

`exec` inside the `sh -c` replaces the shell process via `execve`
rather than forking a child — uvicorn ends up as PID 1 regardless,
receiving `SIGTERM` natively. Render's own docs confirm `dockerCommand`
overriding the Dockerfile `CMD`, and its own multi-command guidance
("provide them to `/bin/sh -c`") sanctions exactly this pattern. Net
effect: the Sprint 9.1 Dockerfile — and its own local validation via
`docker-compose.container.yml` — needed zero changes.

### Decision: `CORS_ALLOWED_ORIGINS` must be a JSON array string

Render's own docs state environment variable values "are always
strings" — there is no native list type. `app/platform/config.py`'s
`cors_allowed_origins: list[str]` is parsed by pydantic-settings as
JSON. Verified empirically this sprint (see Verification): a plain
string value raises `SettingsError`/`JSONDecodeError` at import time —
`settings = Settings()` runs at module load, so a malformed value would
crash the entire backend on boot. `render.yaml` sets the value as
`'["https://tradeos-frontend.onrender.com"]'` — a JSON array encoded as
one string — which parses correctly.

### Decision: explicit `DATABASE_SSL_REQUIRED` flag, not URL parsing

SQLAlchemy's `asyncpg` dialect does not translate a `?sslmode=require`
query parameter on the connection URL — it passes `sslmode` straight
through to `asyncpg.connect()`, which raises `TypeError` (a documented,
open issue on SQLAlchemy's own repository, `sqlalchemy/sqlalchemy#6275`).
Rather than parsing or rewriting whatever connection string Render's
`fromDatabase.connectionString` produces, this sprint adds one explicit,
boolean settings field.

### Added
- `render.yaml` (repo root) — Blueprint IaC for `tradeos-db` (Postgres
  16, matching `backend/docker-compose.yml` and Sprint 9.1's own
  validation, not a newer untested major version), `tradeos-backend`
  (Docker web service, `dockerCommand`, `preDeployCommand: python
  scripts/migrate.py`, `healthCheckPath: /healthz`), and
  `tradeos-frontend` (Static Site, `corepack`-pinned `pnpm@11.10.0`,
  `--frozen-lockfile`, SPA rewrite `/* -> /index.html` for
  `frontend/src/App.tsx`'s `BrowserRouter`).

### Modified
- `backend/app/platform/config.py` — new field `database_ssl_required:
  bool = False`. Default preserves local-dev behavior exactly.
- `backend/app/platform/db/session.py` — `connect_args={"ssl": "require"}`
  passed to `create_async_engine` only when `database_ssl_required` is
  true; empty dict (today's exact behavior) otherwise.

### Explicitly not changed
`backend/Dockerfile`, `backend/docker-compose.container.yml`,
`backend/scripts/migrate.py`, `backend/scripts/bootstrap.py`,
`backend/scripts/seed_configuration.py`, and every API contract,
Domain Model class, and Use Case — confirmed via `git diff --stat`
before implementation and re-confirmed after.

### Verification performed

- **Regression:** `pytest` — 357 passed (unchanged from Sprint 9.1).
  `ruff check` — clean. `ruff format --check` — clean except the same
  one pre-existing, unrelated file from Sprint 8.1. `mypy` — same 9
  pre-existing, unrelated errors in the same 4 files as every prior
  round; none in `config.py` or `session.py`. Frontend: `tsc -b
  --noEmit` — clean. `vitest` — 93 passed (16 files). `eslint` — clean.
  `prettier --check` — 24 pre-existing warnings in
  `src/features/trading/*`, confirmed via `git status` to be untouched
  by this sprint (unrelated pre-existing debt, same pattern as the
  backend's own known formatting debt).
- **`dockerCommand` / PID 1 / signal handling, verified empirically, not
  assumed:** built the (unchanged) Sprint 9.1 image, ran it directly
  with the exact `render.yaml` `dockerCommand` string and `PORT=9000`.
  `/proc/1/cmdline` inside the container showed
  `/usr/local/bin/python3.12 /usr/local/bin/uvicorn ... --port 9000` —
  uvicorn genuinely PID 1, `$PORT` correctly substituted. `docker stop`
  (SIGTERM) completed in 0.77s with the full graceful sequence in the
  logs (`Shutting down` → `Waiting for application shutdown` →
  `Application shutdown complete` → `Finished server process [1]`) —
  no `SIGKILL` needed.
- **`CORS_ALLOWED_ORIGINS` / `DATABASE_SSL_REQUIRED`, verified
  empirically:** a plain string value for `CORS_ALLOWED_ORIGINS`
  reproduces the exact `SettingsError` predicted; the JSON-array format
  used in `render.yaml` parses to `list[str]` correctly.
  `DATABASE_SSL_REQUIRED=true` yields `connect_args={"ssl": "require"}`;
  its absence (today's local dev) yields `connect_args={}`, byte-for-
  byte the pre-Sprint-9.2 behavior.
- **`VITE_API_BASE_URL` baked at build time, verified empirically, not
  assumed:** ran `VITE_API_BASE_URL=https://tradeos-backend.onrender.com/api/v1
  pnpm run build` and grepped the resulting bundle — the literal URL
  string is present in `dist/assets/index-*.js`. Resolves the one
  uncertainty a review round explicitly required closed rather than
  left open in the Technical Plan.
- **Full container smoke test**, same isolated `docker-compose.container.yml`
  stack as Sprint 9.1, `docker build`/`docker compose up` with zero
  changes: `migrate.py` (all 12 revisions apply cleanly) → register a
  real user → `seed_configuration.py --user-id <uuid>` (published `v1.0`)
  → `POST /trades` with `status: "planned"` → **201** → `DELETE
  /trades/{id}` → **204** (soft-delete) → `GET /trades` confirms an
  empty list. Deliberately uses the `planned`/soft-delete path rather
  than leaving synthetic trade data behind, since this sprint's
  container-validation database is structurally the same kind of
  database (managed Postgres) the user's real trading data will live
  in once actually deployed — unlike Sprint 9.1's throwaway local
  container, "smoke test residue" here is not free to ignore.
- **Dev environment integrity:** `backend-postgres-1` and its volume
  (`backend_tradeos_postgres_data`) confirmed untouched throughout,
  exactly as in Sprint 9.1 — the isolated `name:
  tradeos-container-validation` project continues to prevent any
  collision.

### Self-Audit (post-implementation correction pass)

A dedicated, critical re-review of this sprint's own Final Report,
performed before closing the sprint, found two real documentation gaps
and confirmed several other points that were already correct:

- **Documentation gap, fixed:** `TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1
  and `TRADEOS_TECHNICAL_STACK.md` §13 still spoke only of a *class* of
  hosting platform, even though Render had, by this point, actually
  been selected and committed to in `render.yaml` — a real decision
  already made, not merely planned. Both sections now record that
  selection explicitly (a short addition each, not a rewrite), while
  preserving their own class-level architectural reasoning intact,
  exactly as the equivalent `/healthz` amendment in Sprint 9.1 recorded
  a real decision without inventing new architecture.
- **`render.yaml` re-verified line by line against official Render
  documentation, not memory, specifically checking for deprecated
  fields:** confirmed this file uses none of the fields Render's own
  Blueprint reference explicitly flags as deprecated (`env` → `runtime`,
  `autoDeploy` → `autoDeployTrigger`, `afterFirstDeployCommand` →
  `initialDeployHook`, `previewsEnabled`/`pullRequestPreviewsEnabled` →
  `previews.generation`). No change needed — confirmed clean, not
  assumed clean. **Scope of this confirmation, stated precisely:** this
  verifies conformance with Render's published specification, not that
  the Blueprint deploys successfully — that operational validation
  (`render blueprint validate`, if the chosen workflow supports it, or
  the first real deploy itself) remains pending a live Render account,
  same as the rest of this sprint's deployment-execution items.
- **Deploy-ordering, checked, not assumed:** confirmed via Render's own
  Blueprint documentation that a service's `fromDatabase`/`fromService`
  reference creates an automatic provisioning order — `tradeos-db` is
  guaranteed to exist before `tradeos-backend`'s deploy runs. No
  explicit `dependsOn` field exists or is needed; none was missing.
- **Postgres `ipAllowList`, checked, disclosed rather than silently
  accepted:** Render's own default for a new Postgres instance with no
  `ipAllowList` set is "allow all IPs, require valid credentials" —
  this `render.yaml` does not set `ipAllowList`, so it inherits that
  default. This is Render's own stated baseline for managed Postgres,
  not a hole introduced by this sprint, and combined with
  `DATABASE_SSL_REQUIRED` it matches the security posture already
  approved in the Technical Plan. Restricting it further (e.g. to
  Render's own private network) is real hardening work that belongs to
  Sprint 9.3 ("Hardening & Blocking-Question Resolution",
  `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9) — it is a new decision
  requiring its own verification against a live account, not a defect
  in this sprint's own scope.
- **No technical debt introduced by this sprint's own three touched
  files** (`render.yaml`, `config.py`, `session.py`): no `TODO`/`FIXME`,
  no dead code, no duplicated configuration, confirmed by direct
  inspection.
- **Everything else in the original Final Report's hedged statements**
  (no Render account available; provisional `.onrender.com` domain
  names; the real production smoke test) genuinely requires a live
  Render account this environment does not have — correctly left as
  the user's own next step, not something resolvable by further code
  or documentation changes.

### Confirmation

This sprint delivers a complete, internally-verified `render.yaml` and
the two small backend changes it depends on — but **does not** deploy
TradeOS to Render. No Render account is available in this environment.
Applying this Blueprint to a real Render account, resolving the
`.onrender.com` domains it currently references provisionally, and
running the equivalent smoke test against the real managed database
all remain the user's own next steps — not claimed as done here.
`GET /readyz` remains explicitly deferred, not implemented. No
`git push` was run at any point.

## Sprint 9.3 — Hardening & Blocking-Question Resolution

Phase 9 (Deployment & Production Hardening), third and final sprint per
`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9. Scope held deliberately
narrow to exactly what the Master Plan's own Objectives text names —
secrets management (`TRADEOS_SYSTEM_ARCHITECTURE.md` §11.1) and
resolving or explicitly, documentedly deferring every Section 16
blocking Open Question (only OQ-4 remained, OQ-1/OQ-3 already resolved
in Sprint 9.1) — preceded by a full Fase 1-3 review cycle including
three adversarial technical-review rounds on the Plan Técnico (`headers`
field validated against the official Blueprint spec rather than assumed
from other platforms; Content-Security-Policy audited against the real
built bundle, not a generic template; HSTS value checked against MDN
and RFC 6797). During implementation, an explicit rule was followed:
no additional hardening beyond what the approved plan specified, even
where a further improvement seemed obvious — anything noticed is
recorded below as a future observation, not implemented.

### Decision: OQ-4 (encryption at rest) resolved, not deferred

Render Postgres is encrypted at rest using AES-256 — covering primary,
replica, and backup instances — confirmed directly against
[render.com/docs/databases](https://render.com/docs/databases). This is
literally one of the options `TRADEOS_DATABASE_DESIGN.md` §11.4 always
considered acceptable without a schema redesign ("disk-level encryption
via the hosting provider"). Resolves Master Plan OQ-4 and the
encryption-standard component of Product Bible Open Question 3. The
remaining components of that Open Question (staff data access, formal
breach response, compliance regime) stay explicitly open — Product
Bible NFR 10.3 itself conditions them on a multi-user or
hosted-for-others deployment, which TradeOS is not.

### Decision: least-privilege database roles — explicitly deferred, not silently skipped

`TRADEOS_DATABASE_DESIGN.md` §11.3 documents one Postgres role per
module as "a real, recommended provision, not a premature one." It was
never implemented (confirmed: zero `CREATE ROLE`/`GRANT` statements in
any Alembic migration; `app/platform/db/session.py` uses a single
shared engine/role). This sprint registers that status explicitly in
§11.3 itself rather than leaving it an undocumented gap, and defers
implementing it — the Master Plan's own Sprint 9.3 Objectives text
names secrets management and Open-Question resolution, not this;
implementing it correctly means one role per Bounded Context plus
reconnecting every module's infrastructure layer, a materially larger
change disproportionate (Architectural Principle 4) to a confirmed
single-user deployment. Revisit when Product Bible Open Question 2
(multi-user) resolves.

### Decision: `JWT_SECRET_KEY` generated by Render, not hand-pasted

`render.yaml`'s `sync: false` (Sprint 9.2) required a human to paste a
value into the Render dashboard. Changed to `generateValue: true` —
Render generates a randomized, base64-encoded, 256-bit value
automatically, once, the first time the Blueprint is applied (verified
against the Blueprint YAML Reference). Removes the one remaining
human-chosen-strength dependency in this project's secret handling.

### Decision: Security Headers — backend middleware + frontend `render.yaml` headers

`TRADEOS_TECHNICAL_STACK.md` §14 names a standard baseline (CSP,
X-Frame-Options, HSTS, X-Content-Type-Options) "applied at the
static-hosting layer (frontend) and via lightweight middleware
(backend)" — documented since before this sprint, never implemented.

- **Backend:** new `app/platform/middleware/security_headers.py`, an
  ASGI middleware following the same style already established by
  `CorrelationIdMiddleware` (plain ASGI, not `BaseHTTPMiddleware` —
  keeping one middleware style in the project rather than mixing two
  for no reason). Registered as the outermost middleware in `main.py`
  so every response carries these headers, including a 401 from
  `AuthenticationMiddleware` or a CORS preflight answer — verified
  empirically (see Verification). `Content-Security-Policy: default-src
  'none'; frame-ancestors 'none'` — the backend is a pure JSON API, it
  never serves HTML/CSS/JS/images of its own and is never meant to be
  framed, so the strictest possible policy applies with no exceptions
  needed.
- **Frontend:** `render.yaml`'s `tradeos-frontend` service gained a
  `headers` block. Verified this field exists specifically for `runtime:
  static` in the official Blueprint YAML Reference (quote: *"Configuration
  details for a static site's HTTP response headers"*), with the exact
  `path`/`name`/`value` syntax already used for `routes`, cross-checked
  against a real public `render.yaml` example. Content-Security-Policy
  audited against `pnpm run build`'s actual output (`dist/`), not a
  generic template:
  - `default-src 'self'` — the app's own scripts/styles are same-origin.
  - `style-src 'self' 'unsafe-inline'` — the `'unsafe-inline'` exists
    specifically because Radix UI/Floating UI (`@radix-ui/react-*`) and
    `recharts` set inline `style="..."` attributes at runtime for
    positioning; without it, every popover/dialog/select/dropdown and
    every chart in the app would be visually broken. Not a generic
    allowance — grep-verified against the project's real dependency
    tree.
  - `connect-src 'self' https://tradeos-backend.onrender.com` — the
    only network call the SPA makes.
  - `img-src 'self' data:`, `object-src 'none'`, `base-uri 'self'`,
    `frame-ancestors 'none'` — standard hardening with no functional
    cost to this specific app (verified: no `<object>`/`<base>` usage).
  - **Explicitly audited and NOT added**, because the real built bundle
    doesn't need them (`grep` over `dist/assets/*.js` and `*.css`,
    zero matches for each):
    `script-src` (no separate directive needed — the sole script is
    same-origin, already covered by `default-src 'self'`; no `eval`,
    `new Function`, or `blob:` URLs anywhere in the bundle),
    `worker-src` (no Worker/SharedWorker/ServiceWorker anywhere — the
    `StatisticsPage` chunk loads via a same-origin dynamic `import()`,
    which falls under `script-src`, not `worker-src`), `font-src` (zero
    `@font-face`/`.woff`/external font providers — confirmed against
    `index.html` and the built CSS), `media-src` (no audio/video
    anywhere in the app).

### Decision: HSTS — `max-age=31536000`, no `includeSubDomains`, no `preload`

Applied identically to backend and frontend. MDN's own non-preload
example uses exactly `max-age=31536000` (1 year); the longer
`max-age=63072000` example in the same documentation is paired
specifically with `preload`, which this sprint does not propose.
`includeSubDomains` is deliberately omitted: it would extend the policy
to every subdomain of whatever host serves it, and today that host is a
Render-assigned `.onrender.com` subdomain with no subdomains of its own
to protect — reintroducing it unexamined against a future custom root
domain (with subdomains not yet known) is exactly the kind of
unverifiable commitment this project avoids. Revisit once a custom
domain exists with verified HTTPS coverage across every real subdomain.

Whether Render itself also injects an HSTS header automatically could
not be confirmed either way — [render.com/docs/tls](https://render.com/docs/tls)
covers certificate issuance and HTTP→HTTPS redirection but never
mentions HSTS. Documented rather than assumed: per
[RFC 6797 §8.1](https://www.rfc-editor.org/rfc/rfc6797), *"If a UA
receives more than one STS header field in an HTTP response message
over secure transport, then the UA MUST process only the first such
header field"* — if Render did add its own, there is no merge, no
error, and no broken behavior; at most, one of the two policies is
silently ignored by the browser, per spec.

### Added
- `backend/app/platform/middleware/security_headers.py`.

### Modified
- `backend/app/main.py` — imports and registers `SecurityHeadersMiddleware`
  as the outermost middleware.
- `render.yaml` — `JWT_SECRET_KEY` → `generateValue: true`; new `headers`
  block on `tradeos-frontend`.
- `docs/05_TRADEOS_DATABASE_DESIGN.md` v1.2 → v1.3 — §11.3 (status note,
  least-privilege roles deferred), §11.4 (OQ-4 resolved).
- `docs/04__TRADEOS_SYSTEM_ARCHITECTURE.md` v1.2 → v1.3 — §11.2 (OQ-4
  resolved); also retroactively versions the Sprint 9.2 self-audit's
  own addition to §12.1 (recording Render as the selected vendor),
  which had not received its own Document Control entry at the time.

### Explicitly not changed
`backend/Dockerfile`, `backend/docker-compose.container.yml`, every
migration script, every API contract, every Domain Model class, every
Use Case, the Scoring Engine — confirmed via `git diff --stat` before
and after implementation.

### Verification performed
- **Regression:** `pytest` — 357 passed (unchanged). `ruff check` —
  clean. `ruff format --check` — clean except the same one
  pre-existing, unrelated file from Sprint 8.1. `mypy` — same 9
  pre-existing, unrelated errors in the same 4 files as every prior
  round; none in `security_headers.py` or `main.py`. Frontend: `tsc -b
  --noEmit` — clean. `eslint` — clean. `vitest` — 93 passed (16 files,
  unchanged). `pnpm run build` — succeeds, identical output to the
  pre-sprint build (frontend code untouched this sprint).
- **Security headers, verified empirically against a running instance,
  not assumed from the middleware's own source:** started the backend
  locally (`uvicorn`) and inspected real HTTP responses with `curl -D -`.
  A public `GET /healthz` (200) and a protected endpoint without a
  token (401) **both** carried all four headers with the exact
  approved values — confirming the middleware's outermost placement
  correctly covers an authentication rejection, not only successful
  responses.
- **`render.yaml` re-validated as syntactically correct YAML** after
  every edit (`yaml.safe_load`).
- **Every Render-specific claim in this sprint's Plan Técnico was
  checked against Render's own current documentation before
  implementation** (`headers` field existence and scope, `generateValue`
  behavior, encryption-at-rest wording, absence of any HSTS mention) —
  none were assumed from memory or from other platforms' conventions.

### Future observations (explicitly not implemented this sprint, per the approved rule)
Recorded here rather than acted on, exactly as instructed — noticing a
potential improvement during implementation is not authorization to
implement it:
- Once a custom domain exists with verified subdomain HTTPS coverage,
  revisit HSTS: add `includeSubDomains`, consider `preload` and the
  longer `max-age=63072000`.
- `TRADEOS_TECHNICAL_STACK.md` §14.2 also names Dependabot, `pip-audit`,
  `pnpm audit`, and Trivy — all documented, none implemented, all
  blocked on OQ-8 (is GitHub the confirmed code-hosting platform?),
  which this sprint did not touch.
- `TRADEOS_BACKEND_BLUEPRINT.md` §13's "Rate Limiting Hooks" remain
  unimplemented — the document itself states thresholds are "an
  operational tuning decision, not fixed here," so implementing it now
  would mean inventing a number no document specifies.
- Least-privilege database roles (§11.3) — see the Decision section
  above; the deferral itself, and its trigger condition, are now
  written down, not just implied.

### Confirmation
Milestone M9 (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7) is **not**
claimed as achieved — it requires the containerized backend and static
frontend actually running on Render against a real managed database,
which remains pending the user's own account setup (Sprint 9.1/9.2's
own stated pending items, unchanged by this sprint). What this sprint
does close: based on the architectural decisions documented up to this
point in the project, OQ-1, OQ-3, and OQ-4 each have a documented
resolution in their respective reference documents (this sprint did
not re-audit the full, current state of Master Plan §16 itself — that
was outside this sprint's scope). Secrets management has no remaining
gap this project's current single-user scale requires closing. No
`git push` was run at any point.

## Sprint 9.4 — Deployment Readiness & Operational Hardening

Scope, narrowed by explicit user decision after an initial broader
analysis (Fase 1/2): build the project's DevOps/automation foundation —
a minimal CI + security-scanning pipeline — without touching deployment
automation itself. Explicitly out of scope: Render deployment, Auto
Deploy, Staging, Production deployment, Monitoring, Alerting, Error
Tracking, Rate Limiting, Disaster Recovery, Backup verification,
Rollback strategy, Production Checklist — all deferred to a future
sprint, none silently absorbed into this one.

Every workflow-architecture and tooling decision below went through a
dedicated documentary-research pass (Fase 3.1–3.3) before implementation,
each backed by an official source, not assumed from prior experience —
the same standard applied to HSTS/CSP in Sprint 9.3.

### Decision: OQ-8 resolved — GitHub is the confirmed code-hosting platform
`TRADEOS_TECHNICAL_STACK.md` §20 registered this as genuinely open since
the document's initial version: §12's GitHub Actions selection and §14's
Dependabot choice both assumed it "as the most likely default," never
confirmed. Resolved with direct evidence from this repository itself —
`git remote -v` returns `origin git@github.com:Jaiderrtriana/TradeOS.git`
for both fetch and push — not inferred, not assumed. `TRADEOS_TECHNICAL_STACK.md`
bumped 1.0 → 1.1 (its first amendment since being frozen), following the
same pattern already established for `SYSTEM_ARCHITECTURE.md`/`DATABASE_DESIGN.md`
in Sprint 9.3: a status note appended to §12/§14, the Open Question
removed from §20 with its resolution recorded, and both of this
document's own history tables (§1 Document Control, §21 Change Log —
a structural quirk unique to this document, flagged during Fase 1)
updated in lockstep.

### Decision: three separate workflow files, not one `ci.yml` with multiple jobs
Investigated against official GitHub Actions documentation specifically
before designing anything (user-mandated re-verification, turn 3 of
Fase 3): GitHub does not explicitly prescribe either structure. Two
concrete, documented mechanisms decided it instead:
- **Job parallelization and PR check visibility are identical either
  way** — jobs run in parallel by default regardless of file structure
  (`docs.github.com`/articles/getting-started-with-github-actions), and
  GitHub creates one status check per job, not per workflow file,
  confirmed via GitHub's own "Status checks" reference.
- **Only separate workflow files get native `paths` filtering** — a
  change touching only `frontend/` never triggers `backend-ci.yml` or
  `container-scan.yml`, with zero third-party tooling
  (`docs.github.com/actions/using-workflows/triggering-a-workflow`).
  Replicating this inside one multi-job workflow would require a
  third-party action (e.g. `dorny/paths-filter`) GitHub does not ship.

This is the only point where official documentation actually
distinguished the two options — it favored separate files, so that is
what was built.

### Decision: `concurrency` on all three workflows
Official pattern, applied verbatim
(`docs.github.com/en/actions/using-jobs/using-concurrency`):
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
A repeated push to the same PR/branch cancels the previous, now-obsolete
run instead of letting it finish and consume runner minutes for nothing
— most relevant for `container-scan.yml`, the slowest of the three
(Docker build + Trivy scan).

### Decision: Poetry via `pipx install poetry==2.4.1`, not `snok/install-poetry`
The Plan Técnico's first draft proposed the third-party
`snok/install-poetry` action. A dedicated re-verification (user-mandated,
Fase 3.2) against Poetry's own official documentation
(`python-poetry.org/docs/#installation`) found it explicitly recommends
`pipx` as "one of your top choices for use of Poetry in CI" — and never
mentions any third-party GitHub Action. Corrected before implementation:
`pipx install poetry==2.4.1`, with `pipx` already preinstalled on
`ubuntu-24.04` runners (`actions/runner-images`, confirmed version
1.16.0) — no extra dependency, no extra action to SHA-pin and keep
updated, identical functionality for this project's exact need (a
version-pinned Poetry compatible with `actions/setup-python`'s
`cache: 'poetry'`). Version `2.4.1` specifically matches
`backend/poetry.lock`'s own generator header ("automatically @generated
by Poetry 2.4.1") — a different Poetry version risked a different
lockfile format than what's committed.

### Decision: Node 22 in CI, not Node 20
`frontend/package.json` only requires `"node": ">=20"`. Verified against
Node.js's own official EOL page (`nodejs.org/en/about/eol`): **Node 20
reached end-of-life on April 30, 2026** — already unsupported upstream
as of this sprint. Building a brand-new CI pipeline today deliberately
targeting an EOL runtime, only because `>=20` technically allows it,
would be building on a known-unsupported foundation from day one. Node
22 (Maintenance LTS, supported until April 2027) satisfies the existing
constraint without any change to `package.json`.

### Decision: `pnpm/setup`, not `pnpm/action-setup` + `actions/setup-node`
Verified against pnpm's own official CI documentation
(`pnpm.io/continuous-integration`) and the `pnpm/setup` README directly:
`pnpm/action-setup` is explicitly reserved for pnpm v10 and older;
`pnpm/setup` is the current recommendation for v11+, which is what this
project already uses (`render.yaml`: `corepack prepare pnpm@11.10.0`).
`pnpm/setup` also has its own native caching (`cache: true`) and installs
Node in the same step, removing the need for a separate
`actions/setup-node`. Neither action has a working-directory input
(verified against the README), so `install: false` plus explicit
`package-json-file`/`cache-dependency-path` inputs point it at
`frontend/` — the actual `pnpm install --frozen-lockfile` runs as its
own step, scoped by the job's `defaults.run.working-directory`.

### Decision: severity policy for Trivy / `pip-audit` / `pnpm audit`
Investigated per the user's explicit instruction: official documentation
of each tool plus GitHub Security/Actions guidance, before proposing
anything — no threshold invented.
- **Trivy:** `severity: 'CRITICAL,HIGH'` + `exit-code: '1'` is the exact
  example `aquasecurity/trivy-action`'s own README documents for failing
  a build (default `exit-code` is `0` — a no-op unless overridden).
- **`pnpm audit`:** `--audit-level=high` — an officially documented
  option (`pnpm.io/cli/audit`) accepting `low|moderate|high|critical`;
  `high` matches Trivy's threshold for consistency between the two
  configurable scanners.
- **`pip-audit`:** **no severity filter exists.** Confirmed directly
  against its own documentation and repository: a `--min-severity` flag
  was requested upstream and never implemented. It is binary — fail on
  any known vulnerability, or don't fail at all. This is a genuine,
  tool-level asymmetry, not a decision made here to weaken it.

### Decision: `pip-audit` and `pnpm audit` run report-only this sprint
Discovered during implementation, not anticipated in the Plan Técnico:
running `poetry run pip-audit` against the real project found **12
known vulnerabilities in 4 already-existing dependencies**
(`cryptography`, `ecdsa`, `pytest`, `starlette`) — none introduced by
this sprint. Running `pnpm audit --audit-level=high` against the real
frontend found the same pattern: **5 HIGH + 1 CRITICAL** in transitive
`eslint` dependencies (`brace-expansion`, `js-yaml`) — again, pre-existing,
not introduced here. Blocking either build on day one, for CVEs
this sprint's scope (CI infrastructure, not dependency upgrades)
never intended to fix, would misrepresent a scanning-infrastructure
sprint as a broken one. Presented to the user as a genuine implementation
blocker (not improvised): **decision — both run with `continue-on-error: true`
(report-only) for now**, recorded here as known, pre-existing technical
debt for a future dependency-upgrade sprint, not silently ignored. Trivy
was not affected by this — attempted to verify empirically against the
real backend image (`docker build` succeeded; Trivy itself could not run
locally due to a Docker-socket/SELinux permission constraint specific to
this local sandbox, unrelated to the workflow's own logic) — its
CRITICAL/HIGH-blocking configuration was kept as designed, to be
confirmed on the first real CI run.

### Decision: `GITHUB_TOKEN` least privilege
Verified against GitHub's own Security Hardening Guide for GitHub
Actions before assigning any permission. `backend-ci.yml` and
`frontend-ci.yml` declare only `contents: read` — confirmed sufficient,
since checkout, Poetry/pipx, `pnpm/setup`, and every lint/test/build/audit
step in both never call the GitHub API. `container-scan.yml` additionally
needs `security-events: write` for `upload-sarif`, plus `actions: read`
specifically because this repository is private (`gh repo view` confirms
`"visibility":"PRIVATE"`) — the codeql-action documentation names that
extra requirement explicitly for private repositories. No workflow is
granted write access to repository contents.

### Decision: `actions/checkout` hardening
`persist-credentials: false` in all three workflows — GitHub's own
hardening guidance: the default (`true`) leaves a credential in
`.git/config` that a later step could accidentally leak into an
artifact or log, and none of these workflows ever need to push back to
the repository. `fetch-depth` left undeclared: verified directly against
`actions/checkout`'s own README that `1` (a single commit) is already
its default — writing it explicitly would only restate, not change,
existing behavior.

### Decision: all third-party Actions pinned by commit SHA
Per GitHub's own Security Hardening Guide ("Pinning an action to a
full-length commit SHA is currently the only way to use an action as an
immutable release"). Every SHA used
(`actions/checkout@3d3c42e...` v7.0.1, `actions/setup-python@5fda3b9...`
v7.0.0, `pnpm/setup@4700d73...` v2.0.1, `aquasecurity/trivy-action@ed142fd...`
v0.36.0, `github/codeql-action/upload-sarif@5595cca...` v4.37.6) was
fetched directly from each repository's real tag list via the GitHub
API (`gh api repos/<owner>/<repo>/tags`), not typed from memory or
invented. `.github/dependabot.yml`'s `github-actions` ecosystem entry
keeps these updated via reviewed PRs going forward, rather than pinned
forever.

### Decision: `pypa/gh-action-pip-audit` not used; `poetry run pip-audit` instead
The official `pip-audit` GitHub Action expects a `requirements.txt`-style
input; this is a pure-Poetry project with no such file, and Poetry 2.x
moved `poetry export` into a separate plugin not otherwise needed here.
`pip-audit`'s own documented default mode audits "the local environment"
directly — so it was added as a `backend/pyproject.toml` dev dependency
(`pip-audit ^2.10.1`, resolved and locked using Poetry 2.4.1 specifically,
matching the exact version the CI installs, so the regenerated
`poetry.lock` is reproducible between local and CI) and run via
`poetry run pip-audit` against the already-installed environment — no
extra export step, no extra plugin dependency.

### Decision: Trivy scans only the backend image; the frontend has none to scan
`TRADEOS_SYSTEM_ARCHITECTURE.md` §12.1 confirms the frontend ships as a
static build (`runtime: static` in `render.yaml`), never a container —
there is no frontend Docker image for Trivy to scan. `container-scan.yml`
builds `backend/Dockerfile` locally (tagged by commit SHA, never pushed
to any registry — out of this sprint's explicit scope) purely so Trivy
has something to scan, then discards it.

### Files added
- `.github/dependabot.yml`
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`
- `.github/workflows/container-scan.yml`

### Files modified
- `backend/pyproject.toml` — added `pip-audit` to `[tool.poetry.group.dev.dependencies]`.
- `backend/poetry.lock` — regenerated with Poetry 2.4.1 (matching both
  the file's own existing generator version and the CI's pinned
  version) to include `pip-audit` and its transitive dependencies.
- `docs/10_TRADEOS_TECHNICAL_STACK.md` — v1.0 → v1.1 (its first
  amendment): OQ-8 resolved (§20); implementation-status notes added to
  §12 (CI/CD) and §14 (Security Tooling) without altering either
  section's original tool selections; both history tables (§1, §21)
  updated.
- `CHANGELOG.md` — this entry.

### Explicitly not changed
`render.yaml`, `backend/Dockerfile`, `backend/app/**`, `frontend/src/**`,
`docs/04__TRADEOS_SYSTEM_ARCHITECTURE.md`, `docs/05_TRADEOS_DATABASE_DESIGN.md`,
`docs/09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` — nothing in this
sprint's scope touches deployment configuration, application code, or
any document besides the Technical Stack (the only one naming the CI/CD
and security-tooling decisions this sprint implements).

### Validations performed and results
- `python3 -c "import yaml; yaml.safe_load(...)"` against all four new
  YAML files — syntactically valid.
- Backend, re-run locally against the regenerated `poetry.lock` ahead of
  committing, to confirm adding `pip-audit` as a dev dependency
  introduced no regression to the existing toolchain or test suite:
  `poetry run ruff format --check .` (1 pre-existing file needing
  reformatting, unchanged since Sprint 8.1, not touched by this sprint),
  `poetry run ruff check .` (clean), `poetry run mypy .` (9 pre-existing
  errors in the same 4 files as every prior sprint, none new),
  `poetry run pytest` (357 passed, same count as every prior sprint).
- Frontend: `pnpm run lint` (clean), `pnpm run typecheck` (clean),
  `pnpm run test` (93 passed, same count as every prior sprint),
  `pnpm run build` (succeeds; same pre-existing >500kB chunk-size
  warning as before, unrelated to this sprint).
- `poetry run pip-audit` and `pnpm audit --audit-level=high` both
  executed for real against this project (not simulated) — results
  quoted in the Decision above, driving the report-only choice.
- `docker build` of `backend/Dockerfile` executed for real, confirming
  the image `container-scan.yml` will build still succeeds unmodified.
- Every action SHA was resolved against the real, current GitHub API
  response for that repository's tags, not memorized or assumed.

### Future observations (explicitly not implemented this sprint)
- `pip-audit` and `pnpm audit` are report-only, tracking 12 and 6
  pre-existing vulnerabilities respectively — a dependency-upgrade
  sprint (`cryptography`, `ecdsa`, `pytest`, `starlette`, and the
  transitive `eslint` chain) should revisit both and switch them back
  to blocking once resolved.
- Trivy's real behavior against the built backend image was designed
  and documented but not empirically confirmed in this local
  environment (Docker-socket/SELinux constraint, not a workflow defect)
  — the first real CI run is this design's actual first test.
- Playwright E2E, staging auto-deploy, and the production manual-approval
  gate remain exactly as `TRADEOS_TECHNICAL_STACK.md` §12 originally
  described them: decided, not yet built.
- Monitoring, Alerting, Error Tracking, Rate Limiting, Disaster Recovery,
  Backup verification, Rollback strategy, and a consolidated Production
  Checklist were all explicitly scoped out of Sprint 9.4 during Fase 1/2
  and remain open for a future sprint.

### Confirmation
This sprint builds CI and security-scanning infrastructure only — it
does not deploy TradeOS anywhere, automate any deployment step, or
change any business logic, Domain Model, API contract, or database
schema. OQ-8 is resolved with direct evidence from this repository; the
severity-policy asymmetry between Trivy/`pnpm audit` (blocking) and
`pip-audit` (report-only) is a genuine, documented tool limitation, not
an inconsistency introduced by this sprint. No `git push` was run at any
point.
