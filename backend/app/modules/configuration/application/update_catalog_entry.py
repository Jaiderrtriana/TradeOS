"""
UpdateCatalogEntryUseCase — TRADEOS_API_SPECIFICATION.md §6.7, PATCH
/catalogs/{id} ("Rename or edit metadata... does not affect historical
Trades referencing this entry by ID," Domain Invariant DI-09).

Only `name` is editable here — `kind`, `id`, and `is_active` are
deliberately absent from this Use Case's signature: activation state is
the exclusive responsibility of DeactivateCatalogEntryUseCase (approved
scope decision, Sprint 2.2), and DB Design §6.8 lists no other editable
metadata field today.
"""

import uuid
from datetime import datetime, timezone

from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository
from app.platform.errors import ConflictError, NotFoundError


class UpdateCatalogEntryUseCase:
    def __init__(self, repository: CatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, entry_id: uuid.UUID, name: str) -> CatalogEntry:
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            raise NotFoundError(f"No catalog entry with id '{entry_id}'.")

        if name != entry.name:
            conflicting = await self._repository.get_by_kind_and_name(entry.kind, name)
            if conflicting is not None:
                raise ConflictError(
                    f"A '{entry.kind}' catalog entry named '{name}' already exists."
                )

        entry.name = name
        entry.updated_at = datetime.now(timezone.utc)
        await self._repository.update(entry)
        return entry
