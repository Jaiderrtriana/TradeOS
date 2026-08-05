# ADR: `workers: 1` in the Playwright E2E Suite — Configuration Singleton vs. Test Parallelism

**Status:** DECIDED — implemented (`frontend/playwright.config.ts`), reviewed and approved after a dedicated audit comparing it against the alternative (parallel execution with per-worker isolation). Not one of the ten frozen canonical documents; a root-level ADR, same category as `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`, which this document is a direct continuation of.

**Context:** Discovered while closing the environment-bootstrap hotfix that made `trading.spec.ts`/`statistics.spec.ts`/`dashboard.spec.ts`/`journal.spec.ts`/`mistakes.spec.ts` each publish their own `ScoringConfigurationVersion` (`frontend/e2e/helpers/configuration.ts`), so none would depend on another spec file having published one first. That change widened an already-known, already-tolerated 2-file race (`ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`) to 7 files, turning an occasional CI flake into a reliably-reproducing failure. See `CHANGELOG.md`'s "Hotfix — Environment Bootstrap & E2E Test Isolation" entry for the full narrative.

**If you are reading this because you are about to delete `workers: 1`** (to speed up the suite, because it "looks like a leftover debug setting," or while adding a CI pipeline): read Section 4 first. Removing it without addressing what Section 1–3 describe will silently reintroduce a real, reproducing race — not a hypothetical one.

---

## 1. Why exactly one `ScoringConfigurationVersion` can be published, ever

This is not a testing constraint — it is a business rule, present since the very first version of Trading:

- `docs/02_TRADEOS_PRODUCT_BIBLE.md` states as of its own writing: *"TradeOS has exactly one confirmed user: its own builder, using it for personal trading journaling... Nothing in this document should assume multi-user, multi-tenant, or commercial use until that question is resolved"* (§introductory framing, line 111), and NFR 10.4 (Availability) explicitly ties this to a **single-user, personally-hosted** deployment model.
- `TRADEOS_DATABASE_DESIGN.md` §6.6 and migration `0006_scoring_configuration_publish_uniqueness.py` enforce this at the database level with a partial unique index:
  ```sql
  CREATE UNIQUE INDEX ix_scoring_configuration_versions_one_published
  ON configuration.scoring_configuration_versions ((true))
  WHERE status = 'published';
  ```
  The same idiom already used for `evaluation_snapshots.trade_id WHERE is_current = true` — not a one-off, but this schema's established pattern for "exactly one current X."
- `PublishScoringConfigurationVersionUseCase` additionally serializes concurrent publish attempts with a `pg_advisory_xact_lock` (`ScoringConfigurationVersionRepository.lock_for_publish()`), closing the write-skew race documented and fixed in `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`.

There is no `workspace_id`, `tenant_id`, or any per-user scoping column on this table, and no Use Case (`RegisterTradeUseCase`, `OpenTradeUseCase`, `PreviewEvaluationUseCase`, `PublishScoringConfigurationVersionUseCase`) accepts a scoping parameter when it asks "what is the currently published Configuration?" This is deliberate, not an oversight: a single-admin product has exactly one active scoring rulebook at a time, by definition.

## 2. Why that makes it a global singleton — and not just "another shared fixture"

Most cross-test contamination in this suite is already solved by scoping: every spec generates a unique email per test (`Date.now()`/`Math.random()`/`crypto.randomUUID()`), so registered users, their Trades, their Journal entries, their Playbook Setups never collide — each test operates on rows only it can see, filtered by its own `user_id` in every repository query.

`ScoringConfigurationVersion` cannot be scoped this way, even in principle, without changing the domain model: there is exactly one "published" slot in the *entire* `configuration.scoring_configuration_versions` table, shared by every user, every test, every request, all the time. Publishing a new version does not add a parallel, independently-visible version for "your" test — it **supersedes** the one the previous publisher was relying on, for everyone, immediately. This is what makes it a true global singleton rather than an ordinary shared-but-scopable resource: no `WHERE user_id = ?` clause can ever isolate one caller's view of "the published Configuration" from another's, because the domain defines there to be only one, period.

## 3. Why parallel Playwright workers produce a *legitimate* race — not bad test hygiene

Playwright's `fullyParallel: true` runs different spec files as separate OS processes (workers), each driving its own browser, but **all of them talking to the same backend, talking to the same Postgres database**. That is the intended, correct way to run E2E tests against a real stack — the alternative (mocking the backend) would defeat the purpose of E2E coverage entirely, and is explicitly rejected elsewhere in this project's own testing philosophy (real Postgres, real `uvicorn`, never mocked, per every sprint's own verification sections).

Given that shared backend/database, and given Section 2's singleton, the sequence below is not a bug in any individual test — it is the correct, expected behavior of every piece involved, composed in a way that produces a race:

1. Worker A (`evaluation-preview.spec.ts`) creates a criterion, a draft version, a weight, and publishes it — now *its* version is the one `published` row.
2. Worker B (`trading.spec.ts`, via `ensurePublishedConfiguration`) — running concurrently, with no knowledge of A's test, no reason to have any — publishes its own empty version, because *its* precondition ("some Configuration must be published so `POST /trades` doesn't 422") is satisfied by any published version at all.
3. B's publish is not a bug: the advisory lock and partial unique index guarantee the database never ends up with two `published` rows or corrupted state (Section 1) — B's publish succeeds cleanly and correctly *supersedes* A's.
4. A's test, still mid-flight, now asserts on a score that only exists if *its specific* criterion is still active in the currently-published version. It is not — B's empty version is now published. A's assertion fails, reading a score of `0`/grade `D` instead of the expected `100`/`A+`.

Every individual step above is the *correct* behavior of the code involved (RegisterTradeUseCase's precondition, the publish Use Case's locking, the test helpers' own scoped responsibilities). The failure is an emergent property of composing correct, independent pieces under a global mutable singleton with no coordination between callers who have no reason to know about each other. This is categorically different from — and should not be mistaken for — "a test left dirty rows behind" or "two tests picked the same username": those are test-hygiene bugs with a local, per-test fix; this is a resource-topology problem that no single spec file can fix on its own, because the resource it depends on is defined, by the domain, to be shared with everyone.

## 4. Why `workers: 1` was chosen (and what was rejected instead)

A dedicated audit (session-scoped, not written to a separate file — see the PR/commit history and `CHANGELOG.md` around this ADR's introduction for the full comparison) evaluated:

- **Keeping `workers > 1` with each spec "fully isolated"**: not achievable without giving each worker its own database, because the singleton (Section 2) cannot be partitioned within one shared database. Rejected as infeasible without the infrastructure investment below.
- **A separate database per worker**: the only way to get real parallelism with real isolation. Requires provisioning, per worker, a dedicated Postgres container *and* a dedicated `uvicorn` process bound to it *and* a dedicated `vite dev` process pointed at that specific backend (this project's frontend reads a single, static `VITE_API_BASE_URL` — there is no per-request tenant routing to switch backends within one frontend instance). This is a materially larger piece of infrastructure than the Testcontainers-per-pytest-session pattern already used for backend integration tests, because those tests exercise the FastAPI app in-process via `httpx.AsyncClient` and never involve a real browser, a real HTTP server, or a real second frontend process — E2E isolation-by-worker means isolating a three-process network topology, not just a database connection.
- **Playwright `projects` / `test.describe.configure({ mode: "serial" })`**: `serial` mode only orders tests *within* one file/worker; two different files both marked serial can still be scheduled to two different workers and race each other exactly as described in Section 3. Playwright's per-project `workers` count is not independently configurable within a single `playwright test` invocation, so "these 7 files never run concurrently with each other, but these other 3 can" is not a first-class, one-command feature — it would require splitting `pnpm test:e2e` into two sequential `playwright test` invocations with different `--project`/`--workers` flags (a real, moderate-complexity option — see Section 5, "Circumstance 2").
- **`workers: 1`** (chosen): removes cross-file concurrency structurally, for the entire suite, with a one-line, zero-infrastructure config change. Cost: full-suite wall-clock time rose from ~20s (6 default workers) to ~67s (1 worker) on this machine.

The deciding factors, in order:

1. **The shared resource is a correct, deliberate domain singleton (Section 1–2), not a test-isolation defect.** There is no per-test fix available that doesn't either change the domain model (multi-tenancy) or build a parallel-environments testing platform (below).
2. **Disproportionate cost for this project's actual scale.** Single maintainer, no CI pipeline configured yet (`.github/` does not exist in this repository), 30 E2E tests. Building N ephemeral (Postgres + backend + frontend) stacks to save under a minute of local wall-clock time contradicts this project's own repeatedly-applied principle of matching tooling investment to actual need (see `docs/10_TRADEOS_TECHNICAL_STACK.md` §16's table of deliberately-rejected, disproportionate alternatives).
3. **Consistency with how this exact class of problem was already solved once.** `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`'s own resolution preferred a structural, database-level guarantee (the partial unique index + advisory lock) over trusting every future caller to coordinate correctly. `workers: 1` is the same preference applied to the test runner: it makes the race impossible by construction, rather than relying on every future spec file's author to remember this ADR and avoid triggering it.
4. **Standard CI runners would not have delivered much real parallelism anyway.** GitHub Actions' standard hosted Linux runners have 2 vCPUs; `fullyParallel: true` with no explicit `workers` cap would have been throttled to a small number of workers in practice, making the *measured* speed cost of `workers: 1` in an eventual CI run smaller than the local 20s→67s difference suggests.

## 5. When to revisit this decision

This is not meant to be permanent. Revisit `workers: 1` specifically if **any** of the following becomes true — and when you do, re-read Sections 1–3 first, because the fix must address the actual resource-scoping problem, not just try a different parallelism knob:

1. **Multi-tenancy ships.** If `docs/02_TRADEOS_PRODUCT_BIBLE.md`'s Open Question 2 (§15, "Is there a business model? ... it affects architecture decisions (multi-tenancy, data isolation) that should not be guessed at") resolves toward offering TradeOS to other traders, `ScoringConfigurationVersion` would need a `workspace_id`/`tenant_id` scope as part of that redesign anyway. Once that column exists, the singleton in Section 2 stops being global — each test's Configuration is scoped to its own workspace, the race in Section 3 disappears at the root, and `workers: 1` should be removed as part of that same change, not before it.
2. **The suite grows large enough that ~1 minute of serialized wall-clock time becomes a real bottleneck** (for local iteration or, once one exists, for CI turnaround). The first thing to try, before building per-worker environments, is the "B-lite" split evaluated and rejected above only for being unnecessary today: separate the 3 spec files that never touch `ScoringConfigurationVersion` (`auth-and-preferences.spec.ts`, `error-banner.spec.ts`, `playbook.spec.ts`, confirmed via `grep` for "New Trade"/Configuration API calls at the time of this ADR) into a `--project` that runs with multiple workers, and keep the remaining Configuration-touching files in a second, serial invocation. This requires no new infrastructure, only a change to `frontend/playwright.config.ts` (projects) and the `test:e2e` script in `frontend/package.json` — re-audit which files touch Configuration before relying on this list, since it will drift as new specs are added.
3. **A CI pipeline is introduced with a real parallel-shard budget** (self-hosted runners, or GitHub Actions with matrix-based sharding across *jobs* rather than Playwright workers within one job). At that point the production-grade pattern is per-shard ephemeral environments — each CI job gets its own complete `docker compose` stack (Postgres + backend + frontend), so parallelism happens *across jobs*, each with full isolation, rather than *within* one Playwright process sharing one database. This is the same infrastructure described as "rejected for now" in Section 4's second bullet, but becomes proportionate once CI infrastructure work is already being done for other reasons.

Until one of these three actually happens, `workers: 1` is not a stand-in for a fix that got skipped — it is the fix, matched to what this project's domain model and scale actually require today.
