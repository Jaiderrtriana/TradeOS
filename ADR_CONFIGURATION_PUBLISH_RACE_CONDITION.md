# ADR: Concurrent-Publish Race Condition in `scoring_configuration_versions`

**Status:** PROPOSED — review document, not yet approved, not yet implemented. Not part of the ten frozen canonical documents; moved into `docs/` (or wherever you direct) only after explicit approval, following the same review-before-commit pattern already used this session for `PROPUESTA_DATOS_BIAS_ENGINE.md`.

**Discovered:** Sprint 3.3 (Evaluation Preview Frontend), while writing `e2e/evaluation-preview.spec.ts`. Reproduced directly against a real Postgres instance, not theorized — see Section 2.

**Affects:** `backend/app/modules/configuration/application/publish_scoring_configuration_version.py` (`PublishScoringConfigurationVersionUseCase`) and `backend/app/modules/configuration/application/create_draft_configuration_version.py` (`CreateDraftConfigurationVersionUseCase`), both reading `ScoringConfigurationVersionRepository.get_published()` (`backend/app/modules/configuration/infrastructure/repository.py`).

---

## 1. Exact mechanism of the race condition

`get_published()` is a plain, unlocked read:

```python
async def get_published(self) -> ScoringConfigurationVersion | None:
    result = await self._session.execute(
        select(ScoringConfigurationVersionModel).where(
            ScoringConfigurationVersionModel.status == "published"
        )
    )
    row = result.scalar_one_or_none()
    return _version_to_domain(row) if row is not None else None
```

`PublishScoringConfigurationVersionUseCase.execute()` then does, all under PostgreSQL's default `READ COMMITTED` isolation:

```python
previously_published = await self._versions.get_published()   # (1) SELECT

version.status = PUBLISHED
version.published_at = datetime.now(timezone.utc)
await self._versions.update_status(version)                    # (2) UPDATE target row

if previously_published is not None:
    previously_published.status = SUPERSEDED
    await self._versions.update_status(previously_published)   # (3) UPDATE the row read in (1)
```

The router commits once, after `execute()` returns — so each *single* call is internally atomic (a crash mid-`execute()` rolls back cleanly). The bug is not intra-transaction atomicity; it is the absence of any **cross-transaction concurrency control** around steps (1)–(3).

Two concurrent publish calls, Transaction A (publishing draft `A`) and Transaction B (publishing draft `B`), both currently seeing version `X` as published:

| Step | Transaction A | Transaction B |
|---|---|---|
| 1 | `SELECT published` → sees `X` | `SELECT published` → sees `X` (A hasn't committed yet) |
| 2 | `UPDATE A SET status='published'` | `UPDATE B SET status='published'` |
| 3 | `UPDATE X SET status='superseded'` | `UPDATE X SET status='superseded'` (redundant, same value) |
| 4 | `COMMIT` | `COMMIT` |

Because A and B write to **different rows** (`A` and `B`, not the same row), Postgres's row-level locking never forces them to serialize — there is no UPDATE-UPDATE conflict on a single row for the database to detect. Both commits succeed independently. Final state: **two rows** (`A` and `B`) simultaneously have `status='published'` — an invariant violation the schema has no constraint to prevent (`TRADEOS_DATABASE_DESIGN.md` §6.6 lists only `version_label` as a Unique Constraint on this table).

This is a textbook **write skew**: each transaction's decision ("what do I need to supersede?") is based on a read that the other transaction's write silently invalidates, and neither row-level locking nor `READ COMMITTED` isolation catches it, because the conflict is a *multi-row invariant* ("at most one `published` row across the table"), not a single-row write conflict.

A second, distinct code path shares the same unlocked read and produces a **different** failure shape:

```python
# CreateDraftConfigurationVersionUseCase.execute()
published = await self._versions.get_published()
if published is not None:
    for weight in await self._weights.list_by_version(published.id):
        await self._weights.add(ScoringWeight(configuration_version_id=draft.id, ...))
```

If this read happens *before* a concurrent publish commits, the new draft's "copy forward the published version's weights" step silently copies from a version that is about to be (or already has been) superseded — the draft is created successfully, with no error, but its starting weights are already stale relative to the version that ends up actually published.

## 2. Scenarios in which it occurs

1. **Two concurrent `POST /configuration/versions/{id}/publish` calls** — e.g., two browser tabs, or a frontend retry-on-timeout that resubmits a publish the server actually already processed.
2. **Parallel automated test suites** — reproduced directly this session: `e2e/evaluation-preview.spec.ts` and `e2e/configuration-and-catalogs.spec.ts` each publish their own Configuration version; run as separate Playwright workers (the default), their publishes raced and produced both failure modes below in the same local Postgres instance.
3. **A script racing a live request** — e.g., `scripts/seed_configuration.py` (which itself calls `create_draft` → `publish`) run at the same time as any user action that also publishes.
4. **`CreateDraftConfigurationVersionUseCase` racing a concurrent `PublishScoringConfigurationVersionUseCase`** — a new draft can silently start from stale weights even when the draft-creation call itself never touches `publish`.

Given the single-admin, "modest availability" context (`TRADEOS_PRODUCT_BIBLE.md` NFR 10.4), scenario 1 is unlikely in today's actual usage pattern. Scenarios 2–3 are not: they are exactly the kind of automated, concurrent access this project's own testing/tooling already performs, and will keep performing as the test suite grows.

## 3. Real impact on data

Both failure modes were reproduced directly against a real Postgres instance this session (not simulated):

- **Crash (`MultipleResultsFound`).** Once two rows share `status='published'`, **every** subsequent call to `get_published()` raises `sqlalchemy.exc.MultipleResultsFound` — not just for the two racing requests. This means `PreviewEvaluationUseCase` (i.e. **every** `POST /evaluation/preview` call) and `CreateDraftConfigurationVersionUseCase` (every new draft) start failing with a 500 for **all users**, persisting until someone manually repairs the data — there is no self-healing path. This was fixed by hand this session via a direct `UPDATE ... SET status='superseded'` against the local dev database; nothing in the running system detects or recovers from this state on its own.
- **Silent data loss.** Observed directly: after two concurrent publishes, exactly one row ended up `published` (no crash that time), but the criterion/weight added for one of the two racing flows was **not** part of the version that ended up published — `PreviewEvaluationUseCase` silently scored as if that criterion had a zero weight, with no error anywhere. In a real deployment this means a configuration change (a criterion someone just weighted and published) can be silently dropped from what Evaluation actually uses, with the API returning `200 OK` to the caller who made that change.

The asymmetry matters: the *trigger* is rare in today's single-admin usage, but the *blast radius* of the crash mode is total (it breaks Evaluation Preview for everyone, not just the two racing calls) and persistent (it does not resolve itself). That combination is why this is being addressed structurally rather than left as a documented risk.

## 4. Candidate solutions

### 4.1 `SELECT ... FOR UPDATE`

Lock the currently-published row (or a dedicated sentinel resource, since "the published row" doesn't exist yet on the very first publish) before deciding what to supersede, forcing a second concurrent transaction to block until the first commits and then re-read the true current state.

- **Pros:** correctness, once applied consistently; no schema change beyond an optional sentinel row; conceptually simple ("a mutex around publishing").
- **Cons:** only as strong as its weakest call site — every current *and future* code path that reads `get_published()` for a write decision must also take the lock, or the protection silently has a hole. Does not, by itself, stop someone from writing a new Use Case tomorrow that reads `get_published()` unlocked.

### 4.2 Optimistic locking (row versioning / `xmin`)

Version the row (or a sentinel "current published version_id" row) and use compare-and-swap semantics: a write only succeeds if the row hasn't changed since it was read; the loser detects zero-rows-affected and retries.

- **Pros:** non-blocking; Postgres's built-in `xmin` gives free conflict detection with no new column.
- **Cons:** protects a *single row's* consistency, not the cross-row invariant ("at most one `published` row in the whole table") — to apply it to *this* problem you still need a sentinel resource representing that invariant, same structural requirement as 4.1, plus explicit retry logic. Optimistic locking pays off under real contention; this table has essentially none (publishing is a rare, deliberate admin action), so its main advantage (avoiding blocking) has no payoff here.

### 4.3 Partial unique index

```sql
CREATE UNIQUE INDEX one_published_scoring_configuration_version
ON configuration.scoring_configuration_versions ((true))
WHERE status = 'published';
```

Makes "two rows with `status='published'`" physically impossible to persist, regardless of application code, race timing, a forgotten lock, or a future Use Case nobody remembers to lock correctly. This is the **exact same pattern already used elsewhere in this schema** — `TRADEOS_DATABASE_DESIGN.md` §6.12's partial unique index on `evaluation_snapshots.trade_id WHERE is_current = true` — so it is not a novel technique for this codebase, it is the established pattern being under-applied to this table.

- **Pros:** the strongest possible guarantee (a true database-level invariant); requires zero ongoing discipline at any call site, present or future; cheap, purely additive migration; converts the crash mode into a clean, catchable `IntegrityError`/`UniqueViolation` instead of a `MultipleResultsFound` with no recovery path.
- **Cons:** does **not**, by itself, prevent the silent-data-loss mode (§3) — that failure never violates "at most one published row"; it's a separate stale-read problem in `CreateDraftConfigurationVersionUseCase`. Also doesn't decide *which* of two racers "wins" — it just guarantees only one can succeed; the loser needs explicit handling, not just a raw constraint-violation 500.

### 4.4 Other PostgreSQL-level options: `SERIALIZABLE` isolation

Wrap the publish (and ideally the copy-forward) operation in a `SERIALIZABLE` transaction. Postgres's Serializable Snapshot Isolation (SSI) detects the true read/write dependency between the two transactions and aborts one with a `40001 serialization_failure`, which the caller must catch and retry.

- **Pros:** the only option here that structurally addresses **both** failure modes at once (crash and silent data loss), since SSI reasons about the actual dependency graph, not one declared invariant; no new schema object.
- **Cons:** requires the application to handle retry-on-serialization-failure as a first-class case (an inherent SERIALIZABLE cost); scoping it to only these two Use Cases (not the whole app, which would have real throughput cost elsewhere) means careful, per-transaction isolation-level configuration; harder to write a deterministic unit/integration test for than a unique index's behavior (must genuinely provoke concurrent transactions, not just assert a constraint exists).

### 4.5 Use-case atomicity

Not an independent alternative to the above — a **precondition** already satisfied today. `PublishScoringConfigurationVersionUseCase.execute()`'s own statements already run inside one transaction, committed once by the router; a crash mid-execution already rolls back cleanly. The gap is not intra-use-case atomicity, it is the *absence of concurrency control between separate, concurrently-executing invocations* of the use case. Worth stating explicitly since it was asked for directly: making the use case "more atomic" internally would not, on its own, fix anything described in this document.

## 5. Recommendation

A layered fix, not a single technique:

1. **Partial unique index (4.3)** as the primary, non-negotiable defense — makes the invalid state (two published rows) impossible at the database level, eliminating the crash mode entirely and requiring no future discipline. This is the single highest-leverage change, and matches a pattern this schema already trusts elsewhere.
2. **`SELECT ... FOR UPDATE` (4.1)** inside `PublishScoringConfigurationVersionUseCase`, locking the currently-published row (or a small dedicated sentinel row/advisory lock for the "nothing published yet" case) before deciding what to supersede. This is what actually fixes the *silent data loss* mode, which the unique index alone does not touch — a losing concurrent publisher blocks and re-reads the true current state instead of proceeding on stale data.
3. **Apply the same lock in `CreateDraftConfigurationVersionUseCase`'s copy-forward step**, so a new draft is never silently seeded from a version that's already been (or is about to be) superseded.
4. **Catch the now-rare, now-well-defined conflict** (unique-index violation, or a lock-timeout if one is configured) and translate it to the existing `ConflictError` (409) shape — "Another publish just happened; refresh and try again" — consistent with how this same Use Case already returns 409 for "already published/superseded" today. This is a new *reason* for an existing error code, not a new code — flagged here explicitly rather than assumed, since it's a small but real semantic expansion worth your sign-off.

**Not recommended as the primary mechanism:** optimistic locking (4.2) — this table has no real write contention to justify it, and it still needs the same sentinel-resource design as 4.1 without the throughput payoff. **Not recommended as the primary mechanism, but worth keeping in mind as a future alternative:** blanket `SERIALIZABLE` (4.4) — more powerful in principle, but a bigger operational and testing lift than combining 4.3+4.1, which reach the same practical correctness with primitives this codebase already uses and can test deterministically.

## 6. Migration plan (no compatibility break)

1. **Pre-migration data repair.** The migration's `upgrade()` must not assume the target database already satisfies the constraint — a corrupted dev/staging database (like the one repaired by hand this session) would otherwise fail to migrate. Include a corrective step before creating the index: keep only the most-recently-`published_at` row as `published`, set any others found with `status='published'` to `superseded`. Idempotent — a no-op against an already-consistent database.
2. **Migration.** Purely additive: one partial unique index, no column changes, no data model change visible to any existing query.
3. **Application changes** (`FOR UPDATE` locking in the two Use Cases, and the `IntegrityError` → `ConflictError` translation) can ship in the same change as the migration, or the migration alone can ship first as an immediate backstop against the crash mode, with the Use Case-level fix following separately if you'd rather phase it. Both are backend-only; no frontend change, no REST contract change, no new error `code`.
4. **Backward compatibility.** No legitimate existing behavior depends on being able to have two published versions at once — that state is already an invariant violation per the canonical docs (`TRADEOS_DATABASE_DESIGN.md` §6.6's own "never updated once published" narrative). The only user-visible change is that a genuinely concurrent publish race now surfaces a clear, actionable `409` instead of either silent data loss or an opaque `500`.
5. **Rollout order:** (a) run the corrective query in each environment before deploying the migration; (b) deploy the migration; (c) deploy the Use Case-level locking fix; (d) update `CHANGELOG.md` and the test suite per the usual verification discipline, including a regression test that directly provokes two concurrent publishes and asserts one succeeds, the other gets a clean `409`, and exactly one row ends up `published`.

---

Waiting for your review and explicit approval before implementing any of this — nothing in Section 5's recommendation has been applied to the codebase.
