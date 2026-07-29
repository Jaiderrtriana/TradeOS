"""
Regression tests for `app/platform/idempotency.py`'s concurrency-safety
claim (Sprint 4.1, approved design — see CHANGELOG.md): two genuinely
concurrent requests sharing the same `(user_id, idempotency_key)` must
never both succeed in creating a claim — the database's own UNIQUE
constraint is the enforcement mechanism, never a "SELECT to check, then
INSERT" sequence (the exact race `ADR_CONFIGURATION_PUBLISH_RACE_
CONDITION.md` diagnosed and fixed for Configuration's publish flow, and
the failure mode this design was explicitly built to avoid repeating).

A dedicated, isolated Postgres container (not the suite's shared
session-scoped one), matching
tests/configuration/test_publish_concurrency.py's own reasoning: these
tests assert a genuine cross-transaction race, which would be
meaningless to run against a database other tests are concurrently
writing to.
"""

import asyncio
import uuid

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.platform.db.base import Base
from app.platform.db.models import IdempotencyKeyModel
from app.platform.errors import ConflictError
from app.platform.idempotency import (
    Claim,
    StoredResponse,
    claim_idempotency_key,
    store_idempotent_response,
)

USER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def concurrency_engine():
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        engine = create_async_engine(container.get_connection_url())
        async with engine.begin() as conn:
            # Base.metadata is shared and process-wide: conftest.py
            # unconditionally imports every module's models (so every
            # test file's create_all sees the same full metadata), so
            # every schema any module declares must exist here too, even
            # though this suite only actually touches `platform`.
            for schema in (
                "platform",
                "identity",
                "preferences",
                "configuration",
                "trading",
                "journal",
            ):
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            await conn.run_sync(Base.metadata.create_all)
            # This suite never actually inserts an identity.user_accounts
            # row (USER_ID is a bare uuid4) -- the FK is dropped here so
            # these tests can focus purely on the idempotency_keys
            # constraint itself, exactly as test_publish_concurrency.py
            # only ever seeds the minimal rows its own race needs.
            await conn.execute(
                text(
                    "ALTER TABLE platform.idempotency_keys "
                    "DROP CONSTRAINT idempotency_keys_user_id_fkey"
                )
            )
        yield engine
        await engine.dispose()


async def _make_session(engine) -> "async_sessionmaker":  # type: ignore[name-defined]
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def test_concurrent_claims_for_the_same_key_never_both_succeed(concurrency_engine):
    """The exact scenario the design is built for: two identical requests,
    same Idempotency-Key, arriving at the same time. Before commit, the
    UNIQUE constraint must let exactly one INSERT through; the other must
    either see the (still in-flight) claim and raise ConflictError, or --
    if it loses the race after the first already committed a response --
    replay that response. It must never silently create two claims."""
    key = f"key-{uuid.uuid4()}"
    session_factory = await _make_session(concurrency_engine)

    async def _claim_then_commit():
        async with session_factory() as session:
            result = await claim_idempotency_key(
                session, user_id=USER_ID, idempotency_key=key, endpoint="POST /trades"
            )
            if isinstance(result, Claim):
                await store_idempotent_response(
                    session, result, status=201, body={"id": str(uuid.uuid4())}
                )
            await session.commit()
            return result

    results = await asyncio.gather(
        _claim_then_commit(), _claim_then_commit(), return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            assert isinstance(
                result, ConflictError
            ), f"Unexpected exception from a concurrent claim: {result!r}"
        else:
            assert isinstance(result, (Claim, StoredResponse))

    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(IdempotencyKeyModel).where(
                        IdempotencyKeyModel.user_id == USER_ID,
                        IdempotencyKeyModel.idempotency_key == key,
                    )
                )
            )
            .scalars()
            .all()
        )

    # The real regression: exactly one row for this key must ever exist,
    # never two -- and it must carry a real, completed response.
    assert len(rows) == 1
    assert rows[0].response_status == 201


async def test_sequential_replay_after_first_claim_completes(concurrency_engine):
    """Not a race -- the ordinary case: a client retries the same request
    (e.g. after a dropped connection) once the first attempt has already
    finished. The second call must replay the exact stored response, never
    re-run the wrapped Use Case a second time."""
    key = f"key-{uuid.uuid4()}"
    session_factory = await _make_session(concurrency_engine)
    trade_id = str(uuid.uuid4())

    async with session_factory() as session:
        claim = await claim_idempotency_key(
            session, user_id=USER_ID, idempotency_key=key, endpoint="POST /trades"
        )
        assert isinstance(claim, Claim)
        await store_idempotent_response(session, claim, status=201, body={"id": trade_id})
        await session.commit()

    async with session_factory() as session:
        replay = await claim_idempotency_key(
            session, user_id=USER_ID, idempotency_key=key, endpoint="POST /trades"
        )

    assert isinstance(replay, StoredResponse)
    assert replay.status == 201
    assert replay.body == {"id": trade_id}


async def test_unique_index_rejects_a_direct_duplicate_insert_at_the_database_level(
    concurrency_engine,
):
    """The structural backstop, independent of the application-level
    SAVEPOINT logic: even a direct SQL write bypassing claim_idempotency_key
    entirely cannot create two rows for the same (user_id, idempotency_key)
    -- the database itself refuses it."""
    key = f"key-{uuid.uuid4()}"
    session_factory = await _make_session(concurrency_engine)

    async with session_factory() as session:
        session.add(
            IdempotencyKeyModel(
                id=uuid.uuid4(), user_id=USER_ID, idempotency_key=key, endpoint="POST /trades"
            )
        )
        await session.commit()

    async with session_factory() as session:
        session.add(
            IdempotencyKeyModel(
                id=uuid.uuid4(), user_id=USER_ID, idempotency_key=key, endpoint="POST /trades"
            )
        )
        try:
            await session.commit()
            raised = False
        except IntegrityError:
            await session.rollback()
            raised = True

    assert raised, "the unique index should have rejected a second row for the same key"
