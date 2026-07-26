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
