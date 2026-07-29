"""ListCatalogEntriesUseCase — TRADEOS_API_SPECIFICATION.md §6.7, GET
/catalogs (filterable by `kind`)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository


class ListCatalogEntriesUseCase:
    def __init__(self, repository: CatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, kind: str | None = None) -> list[CatalogEntry]:
        return await self._repository.list_all(kind)


def build_list_catalog_entries_use_case(session: AsyncSession) -> ListCatalogEntriesUseCase:
    """Factory exposed so another module's Application layer (Sprint 5.2:
    Mistakes' `GetMistakeRankingUseCase`, resolving each tag's `name`/
    `is_active`) can list catalog entries without ever importing
    Configuration's infrastructure layer directly — same pattern as
    `build_get_catalog_entry_use_case`."""
    return ListCatalogEntriesUseCase(CatalogEntryRepository(session))
