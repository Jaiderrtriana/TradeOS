"""
Shared test fixtures.

Integration tests run against a real, ephemeral PostgreSQL instance via
Testcontainers (TRADEOS_TECHNICAL_STACK.md §10.2) — never a mock or an
in-memory substitute standing in for Postgres-specific behavior (JSONB,
schemas) this project's models rely on.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.modules.configuration.infrastructure import models as configuration_models
from app.modules.identity.infrastructure import models as identity_models  # noqa: F401
from app.modules.preferences.infrastructure import models as preferences_models  # noqa: F401
from app.platform.db import models as platform_models  # noqa: F401  (registers metadata)
from app.platform.db.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        yield container


@pytest_asyncio.fixture
async def db_session(postgres_container):
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS platform"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS preferences"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS configuration"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        # Mirrors alembic/versions/0004_create_configuration_schema.py's
        # own bulk_insert seed — Base.metadata.create_all only creates
        # tables, it does not run migrations' data seeds. Guarded by a
        # existence check (not a bare insert) because postgres_container is
        # session-scoped: every test function gets a fresh db_session
        # fixture call against the same already-seeded database.
        already_seeded = (
            await session.execute(select(configuration_models.EngineTypeModel).limit(1))
        ).scalar_one_or_none()
        if already_seeded is None:
            session.add_all(
                [
                    configuration_models.EngineTypeModel(
                        code="confidence", display_name="Trade Confidence", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="quality", display_name="Trade Quality", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="execution", display_name="Execution Score", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="market_context",
                        display_name="Market Context Score",
                        is_signed=False,
                    ),
                    configuration_models.EngineTypeModel(
                        code="bias", display_name="Bias Index", is_signed=True
                    ),
                    configuration_models.ScoringProfileModel(
                        code="day_trading", display_name="Day Trading"
                    ),
                    configuration_models.ScoringProfileModel(
                        code="swing_trading", display_name="Swing Trading"
                    ),
                    configuration_models.ScoringProfileModel(
                        code="scalping", display_name="Scalping"
                    ),
                ]
            )
            await session.commit()
        yield session

    await engine.dispose()
