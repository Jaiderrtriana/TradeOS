"""ListCatalogEntriesUseCase — TRADEOS_API_SPECIFICATION.md §6.7, GET
/catalogs (filterable by `kind`)."""

from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository


class ListCatalogEntriesUseCase:
    def __init__(self, repository: CatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, kind: str | None = None) -> list[CatalogEntry]:
        return await self._repository.list_all(kind)
