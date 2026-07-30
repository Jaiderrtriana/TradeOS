"""
Regression test for the 1:1 `catalog_entry_id` linkage under real
concurrency — two genuinely concurrent database transactions (not a
sequential simulation), same dedicated-engine pattern as
`tests/configuration/test_publish_concurrency.py`.

`CreatePlaybookSetupUseCase`'s pre-check (`get_by_catalog_entry_id`)
alone cannot close this race -- two concurrent calls can both pass the
pre-check before either commits, in which case the schema's own
`UNIQUE` constraint on `playbook_setups.catalog_entry_id` is the real
backstop, surfaced as `ConflictError` (409) on the loser. Depending on
actual `asyncio` scheduling, the loser may instead simply lose the race
to the pre-check itself (the winner's commit lands first, so the
loser's own pre-check now sees it and raises `UnprocessableEntityError`,
422) -- both are correct, non-duplicating outcomes; the real regression
this test guards is "never two rows," not "which of the two error paths
fires."
"""

import asyncio
import uuid

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.configuration.infrastructure import models as configuration_models
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository
from app.modules.playbook.application.create_playbook_setup import CreatePlaybookSetupUseCase
from app.modules.playbook.infrastructure import models as playbook_models
from app.modules.playbook.infrastructure.repository import PlaybookSetupRepository
from app.platform.db.base import Base
from app.platform.errors import ConflictError, UnprocessableEntityError


@pytest_asyncio.fixture
async def concurrency_engine():
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        engine = create_async_engine(container.get_connection_url())
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS platform"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS preferences"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS configuration"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS trading"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS journal"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS playbook"))
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                configuration_models.CatalogEntryModel(
                    id=uuid.uuid4(), kind="setup", name="Concurrency Setup", is_active=True
                )
            )
            await session.commit()
            result = await session.execute(select(configuration_models.CatalogEntryModel))
            catalog_entry_id = result.scalar_one().id

        yield engine, catalog_entry_id
        await engine.dispose()


async def _create_setup(session_factory, catalog_entry_id: uuid.UUID):
    async with session_factory() as session:
        use_case = CreatePlaybookSetupUseCase(
            PlaybookSetupRepository(session),
            GetCatalogEntryUseCase(CatalogEntryRepository(session)),
            session,
        )
        setup = await use_case.execute(catalog_entry_id)
        await session.commit()
        return setup


async def test_concurrent_creates_for_the_same_catalog_entry_never_both_commit(
    concurrency_engine,
):
    engine, catalog_entry_id = concurrency_engine
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    results = await asyncio.gather(
        _create_setup(session_factory, catalog_entry_id),
        _create_setup(session_factory, catalog_entry_id),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"expected exactly one winner, got: {results!r}"
    assert len(failures) == 1
    # Either error path is a correct outcome (see module docstring) --
    # what must never happen is an unhandled exception of any other kind.
    assert isinstance(failures[0], (ConflictError, UnprocessableEntityError))

    async with session_factory() as session:
        rows = await session.execute(
            select(playbook_models.PlaybookSetupModel).where(
                playbook_models.PlaybookSetupModel.catalog_entry_id == catalog_entry_id
            )
        )
        assert len(rows.scalars().all()) == 1
