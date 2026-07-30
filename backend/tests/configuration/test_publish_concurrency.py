"""
Regression tests for the concurrent-publish race condition documented and
approved in `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`. Reproduces the
actual scenario (two real, concurrent database transactions — not a
sequential simulation) rather than merely asserting the fix's individual
pieces exist.

A dedicated, isolated Postgres container (not the suite's shared
session-scoped one) — this test asserts a *global* invariant ("at most one
row in the whole table has `status='published'`"), which would be
meaningless to check against a database other tests are concurrently
publishing into.
"""

import asyncio
import uuid

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.modules.configuration.application.create_draft_configuration_version import (
    CreateDraftConfigurationVersionUseCase,
)
from app.modules.configuration.application.create_scoring_criterion import (
    CreateScoringCriterionUseCase,
)
from app.modules.configuration.application.publish_scoring_configuration_version import (
    PublishScoringConfigurationVersionUseCase,
)
from app.modules.configuration.application.update_draft_weights import UpdateDraftWeightsUseCase
from app.modules.configuration.infrastructure import models as configuration_models
from app.modules.configuration.infrastructure.repository import (
    EngineTypeRepository,
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringProfileRepository,
    ScoringWeightRepository,
)
from app.platform.db.base import Base
from app.platform.errors import ConflictError
from app.platform.events.dispatcher import dispatcher


@pytest_asyncio.fixture
async def concurrency_engine():
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        engine = create_async_engine(container.get_connection_url())
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS platform"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS preferences"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS configuration"))
            # Base.metadata is shared and process-wide (conftest.py
            # unconditionally imports every module's models, Sprint 4.1
            # added `trading`, Sprint 5.1 added `journal`) -- every schema
            # any module declares must exist here too, even though this
            # suite only touches `configuration`.
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS trading"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS journal"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS playbook"))
            await conn.run_sync(Base.metadata.create_all)
            # Migration 0006's index isn't applied by `create_all` (that
            # only creates tables/columns, not this hand-written partial
            # index) -- created directly here so these tests exercise the
            # exact same constraint the real migration adds.
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX ix_scoring_configuration_versions_one_published
                    ON configuration.scoring_configuration_versions ((true))
                    WHERE status = 'published'
                    """
                )
            )

        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all(
                [
                    configuration_models.EngineTypeModel(
                        code="confidence", display_name="Trade Confidence", is_signed=False
                    ),
                    configuration_models.ScoringProfileModel(
                        code="day_trading", display_name="Day Trading"
                    ),
                ]
            )
            await session.commit()

        yield engine
        await engine.dispose()


async def _make_session(engine) -> "async_sessionmaker":  # type: ignore[name-defined]
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _create_criterion(session_factory, criterion_id: str) -> None:
    async with session_factory() as session:
        use_case = CreateScoringCriterionUseCase(
            ScoringCriterionRepository(session), EngineTypeRepository(session)
        )
        await use_case.execute(
            id=criterion_id,
            engine_type_code="confidence",
            name=criterion_id,
            source_field=criterion_id,
            min_value=0,
            max_value=100,
            category_map={"Yes": 100, "No": 0},
        )
        await session.commit()


async def _create_draft_with_weight(session_factory, criterion_id: str, label: str) -> uuid.UUID:
    async with session_factory() as session:
        version_repo = ScoringConfigurationVersionRepository(session)
        weight_repo = ScoringWeightRepository(session)
        draft = await CreateDraftConfigurationVersionUseCase(version_repo, weight_repo).execute(
            label
        )
        await session.commit()

    async with session_factory() as session:
        use_case = UpdateDraftWeightsUseCase(
            ScoringConfigurationVersionRepository(session),
            ScoringWeightRepository(session),
            ScoringCriterionRepository(session),
            ScoringProfileRepository(session),
        )
        await use_case.execute(draft.id, criterion_id, "day_trading", 1.0)
        await session.commit()

    return draft.id


async def _publish(session_factory, version_id: uuid.UUID):
    async with session_factory() as session:
        use_case = PublishScoringConfigurationVersionUseCase(
            ScoringConfigurationVersionRepository(session),
            ScoringWeightRepository(session),
            ScoringCriterionRepository(session),
            dispatcher,
            session,
        )
        result = await use_case.execute(version_id)
        await session.commit()
        return result


async def test_concurrent_publishes_serialize_instead_of_both_committing(concurrency_engine):
    """The exact scenario from the ADR: two drafts, published at the same
    time from two independent database sessions. Before the fix, both
    could commit as `published` simultaneously (or one could silently
    supersede a version the other had already moved past). After the fix
    (`lock_for_publish()`), the second caller blocks until the first
    commits, then re-reads the true current state -- both publishes
    succeed, correctly serialized, and the invariant "at most one
    published row" holds throughout."""
    session_factory = await _make_session(concurrency_engine)
    await _create_criterion(session_factory, "confidence.concurrency_a")
    await _create_criterion(session_factory, "confidence.concurrency_b")

    draft_a = await _create_draft_with_weight(
        session_factory, "confidence.concurrency_a", "v-concurrency-a"
    )
    draft_b = await _create_draft_with_weight(
        session_factory, "confidence.concurrency_b", "v-concurrency-b"
    )

    results = await asyncio.gather(
        _publish(session_factory, draft_a),
        _publish(session_factory, draft_b),
        return_exceptions=True,
    )

    # Neither call may crash with MultipleResultsFound or any other
    # unhandled exception -- a legitimate ConflictError (409) would also
    # be an acceptable outcome for the loser, but with lock_for_publish()
    # serializing them, both are expected to succeed.
    for result in results:
        if isinstance(result, Exception):
            assert isinstance(
                result, ConflictError
            ), f"Unexpected exception from a concurrent publish: {result!r}"

    async with session_factory() as session:
        published_result = await session.execute(
            select(configuration_models.ScoringConfigurationVersionModel).where(
                configuration_models.ScoringConfigurationVersionModel.status == "published"
            )
        )
        published_rows = published_result.scalars().all()

    # The real regression: this must never be 2 (or crash while counting).
    assert len(published_rows) == 1
    assert published_rows[0].id in (draft_a, draft_b)


async def test_partial_unique_index_rejects_a_second_published_row_at_the_database_level(
    concurrency_engine,
):
    """A lower-level check independent of the application lock: even a
    direct SQL write that tries to bypass PublishScoringConfigurationVersionUseCase
    entirely cannot create two published rows -- the database itself
    refuses it. This is the structural backstop
    ix_scoring_configuration_versions_one_published exists for."""
    session_factory = await _make_session(concurrency_engine)
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO configuration.scoring_configuration_versions
                    (id, version_label, status, published_at, created_at)
                VALUES
                    (gen_random_uuid(), 'v-direct-1', 'published', now(), now())
                """
            )
        )
        await session.commit()

    async with session_factory() as session:
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO configuration.scoring_configuration_versions
                        (id, version_label, status, published_at, created_at)
                    VALUES
                        (gen_random_uuid(), 'v-direct-2', 'published', now(), now())
                    """
                )
            )
            await session.commit()
            raised = False
        except IntegrityError:
            await session.rollback()
            raised = True

    assert raised, "the partial unique index should have rejected a second published row"


async def test_concurrent_create_draft_never_copies_a_torn_mix_of_two_versions(concurrency_engine):
    """The ADR's *other* failure mode: a new draft's "copy forward the
    published version's weights" step racing a concurrent publish. Before
    the fix, the copy-forward's unlocked `get_published()` read could
    return a version that a concurrent publish was in the middle of
    superseding, silently seeding the new draft from stale data. With
    `lock_for_publish()` also taken here, the copy-forward always reflects
    one complete, real, committed state -- version X's weight or version
    Y's weight, never a mix of both and never neither."""
    session_factory = await _make_session(concurrency_engine)
    await _create_criterion(session_factory, "confidence.torn_x")
    await _create_criterion(session_factory, "confidence.torn_y")

    version_x = await _create_draft_with_weight(session_factory, "confidence.torn_x", "v-torn-x")
    await _publish(session_factory, version_x)

    version_y = await _create_draft_with_weight(session_factory, "confidence.torn_y", "v-torn-y")

    async def _create_new_draft():
        async with session_factory() as session:
            use_case = CreateDraftConfigurationVersionUseCase(
                ScoringConfigurationVersionRepository(session), ScoringWeightRepository(session)
            )
            draft = await use_case.execute("v-torn-new-draft")
            await session.commit()
            return draft.id

    new_draft_id, _ = await asyncio.gather(
        _create_new_draft(),
        _publish(session_factory, version_y),
    )

    async with session_factory() as session:
        weights_result = await session.execute(
            select(configuration_models.ScoringWeightModel).where(
                configuration_models.ScoringWeightModel.configuration_version_id == new_draft_id
            )
        )
        copied_criterion_ids = {row.criterion_id for row in weights_result.scalars().all()}

    # Exactly one complete, real state was copied -- never both (a torn
    # mix) and never neither (a lost read).
    assert copied_criterion_ids in ({"confidence.torn_x"}, {"confidence.torn_y"})
