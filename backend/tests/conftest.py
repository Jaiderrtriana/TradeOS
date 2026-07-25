"""
Shared test fixtures.

Integration tests run against a real, ephemeral PostgreSQL instance via
Testcontainers (TRADEOS_TECHNICAL_STACK.md §10.2) — never a mock or an
in-memory substitute standing in for Postgres-specific behavior (JSONB,
schemas) this project's models rely on.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

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
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
