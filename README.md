# TradeOS

A trading journal application: FastAPI/SQLAlchemy (async) + PostgreSQL backend,
React/TypeScript/Vite frontend. Built per the canonical documents in
[`docs/`](docs/) (`01`–`10`), each with an Implementation Master Plan
(`docs/09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`) driving phased delivery.

This document is the environment setup runbook. It does not describe
product behavior or architecture — see `docs/` for that.

## Prerequisites

- Python 3.12+ ([`backend/pyproject.toml`](backend/pyproject.toml))
- Node.js 20 LTS+ ([`frontend/package.json`](frontend/package.json))
- [Poetry](https://python-poetry.org/) and [pnpm](https://pnpm.io/)
- Docker (for PostgreSQL 16 via `docker compose`)

## 1. Backend

```bash
cd backend
poetry install
docker compose up -d          # PostgreSQL 16 on localhost:5432
cp .env.example .env          # defaults already match docker-compose.yml
```

### Apply migrations and publish the first Configuration

`RegisterTradeUseCase`/`OpenTradeUseCase`/`PreviewEvaluationUseCase` all
require a **published `ScoringConfigurationVersion`** to evaluate against
(`docs/04__TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03) — without one,
`POST /trades` correctly rejects with a 422. Publishing one requires
attributing it to a real, already-registered user
(`docs/09_TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`'s Sprint 2.1 entry:
"Dependencies: Phase 1 (a `user_id` must exist to attribute the seed
action)"), so this is two steps, not one:

```bash
# Stage 1 -- applies all pending migrations. Safe to run before any user exists.
PYTHONPATH=. poetry run python scripts/bootstrap.py

# Start the API so you can register a user:
PYTHONPATH=. poetry run uvicorn app.main:app --reload
```

Register at least one user — either through the frontend's `/register`
page (see Section 2 below) or directly:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'
```

Then look up that user's id (e.g. `docker exec <postgres-container> psql -U tradeos -d tradeos -c "SELECT id, email FROM identity.user_accounts;"`)
and run Stage 2:

```bash
# Stage 2 -- publishes the first ScoringConfigurationVersion, attributed to that user.
PYTHONPATH=. poetry run python scripts/bootstrap.py --user-id <uuid>
```

Both stages are idempotent — re-running `bootstrap.py` (with or without
`--user-id`) is always safe: Alembic skips migrations already applied,
and the Configuration seed skips publishing if a published version
already exists. See [`backend/scripts/bootstrap.py`](backend/scripts/bootstrap.py)
for the full rationale.

### Run the backend test suite

```bash
poetry run pytest
poetry run ruff format --check .
poetry run ruff check .
poetry run mypy .
```

## 2. Frontend

```bash
cd frontend
pnpm install
cp .env.example .env
pnpm dev          # http://localhost:5173
```

```bash
pnpm typecheck
pnpm lint
pnpm test
```

## 3. End-to-end tests

```bash
cd frontend
pnpm test:e2e
```

Requires the backend running and migrated (Stage 1 above is enough —
each spec under `frontend/e2e/` that needs a published Configuration
publishes its own via `frontend/e2e/helpers/configuration.ts`, so no
manual `--user-id` seeding is required for the E2E suite itself).

## 4. Verifying the environment is fully operational

After Stage 1 + Stage 2 above, confirm the golden path works end to end:

1. Register a user and log in (frontend `/register`, `/login`).
2. Create a Trade (`+ New Trade`) — it is evaluated synchronously; no 422.
3. Close it and view its Evaluation.
4. Open `/dashboard` — metrics and the Recent Trades preview render.

If step 2 returns a 422 with `"No configuration version is available to
evaluate against."`, Stage 2 (`bootstrap.py --user-id <uuid>`) has not
been run yet against this database.
