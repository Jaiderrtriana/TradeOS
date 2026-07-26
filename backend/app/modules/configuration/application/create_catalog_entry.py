"""
CreateCatalogEntryUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.7, POST /catalogs.

Business Rules Applied: `(kind, name)` uniqueness
(TRADEOS_DATABASE_DESIGN.md §6.8's unique constraint, enforced here for the
API's own error envelope shape); `kind` must be one of the five confirmed
kinds. No event published (Open Question BE-3: only deactivation is
named).
"""

from app.modules.configuration.domain.catalog_entry import VALID_KINDS, CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository
from app.platform.errors import ConflictError, UnprocessableEntityError


class CreateCatalogEntryUseCase:
    def __init__(self, repository: CatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, kind: str, name: str) -> CatalogEntry:
        if kind not in VALID_KINDS:
            raise UnprocessableEntityError(
                f"'{kind}' is not a valid catalog kind. Expected one of: {sorted(VALID_KINDS)}."
            )

        existing = await self._repository.get_by_kind_and_name(kind, name)
        if existing is not None:
            raise ConflictError(f"A '{kind}' catalog entry named '{name}' already exists.")

        entry = CatalogEntry(kind=kind, name=name)
        await self._repository.add(entry)
        return entry
