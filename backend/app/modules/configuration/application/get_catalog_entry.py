"""
GetCatalogEntryUseCase — a small, new, pure-read Use Case added in
Sprint 4.1: resolves a single `CatalogEntry` by id. No endpoint needs
this directly (`GET /catalogs` — `ListCatalogEntriesUseCase` — already
covers the presentation layer), but `RegisterTradeUseCase`
(`app/modules/trading/application/register_trade.py`) needs to validate
that each of a Trade's optional `strategy_id`/`setup_id`/`session_id`/
`entry_trigger_id` references an existing, *active* catalog entry
(`TRADEOS_API_SPECIFICATION.md` §6.4) — added here, in Configuration's
own Application layer, rather than letting Trading reach into
Configuration's repository directly
(`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3, Forbidden Dependencies), mirroring
`get_configuration_version.py`'s own cross-module factory (Sprint 3.2).
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository


class GetCatalogEntryUseCase:
    def __init__(self, repository: CatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, entry_id: UUID) -> CatalogEntry | None:
        return await self._repository.get_by_id(entry_id)


def build_get_catalog_entry_use_case(session: AsyncSession) -> GetCatalogEntryUseCase:
    """Factory exposed so Trading's Application layer (`RegisterTradeUseCase`)
    can resolve a catalog entry without ever importing Configuration's
    infrastructure layer directly — same pattern as
    `build_get_configuration_version_use_case` (Sprint 3.2)."""
    return GetCatalogEntryUseCase(CatalogEntryRepository(session))
