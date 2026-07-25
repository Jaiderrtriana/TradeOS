"""
Platform: database engine and session factory.

SQLAlchemy 2.0, async, asyncpg driver — per TRADEOS_TECHNICAL_STACK.md §7.
Cross-cutting: every module's own infrastructure layer builds its
repositories on top of this same engine/session factory, never a second one
(TRADEOS_SYSTEM_ARCHITECTURE.md §11.1, least-privilege data access is a
module-boundary concern, not a connection-pooling one).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.platform.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — one session per request, closed automatically."""
    async with SessionLocal() as session:
        yield session
