"""
DeactivateCatalogEntryUseCase — TRADEOS_API_SPECIFICATION.md §6.7, POST
/catalogs/{id}/deactivate. Domain Invariant DI-10: deactivate, never
delete. Publishes `CatalogEntryDeactivated` (TRADEOS_DOMAIN_MODEL.md §11 —
the only Catalogs event named anywhere in the frozen documents; Create/
Update publish nothing, per Open Question BE-3).

Reactivation is explicitly out of scope: TRADEOS_DOMAIN_MODEL.md §13.3
diagrams a reactivate transition, but neither
TRADEOS_API_SPECIFICATION.md §6.7 nor TRADEOS_BACKEND_BLUEPRINT.md §4.8
name a reactivate endpoint or Use Case — this sprint follows the API
Specification/Backend Blueprint's literal, narrower contract rather than
inventing one. See CHANGELOG.md, Sprint 2.2.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository
from app.platform.errors import NotFoundError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class DeactivateCatalogEntryUseCase:
    def __init__(
        self,
        repository: CatalogEntryRepository,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher
        self._session = session

    async def execute(self, entry_id: uuid.UUID) -> CatalogEntry:
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            raise NotFoundError(f"No catalog entry with id '{entry_id}'.")

        entry.is_active = False
        entry.updated_at = datetime.now(timezone.utc)
        await self._repository.update(entry)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="CatalogEntryDeactivated",
                aggregate_type="CatalogEntry",
                aggregate_id=entry.id,
                payload={"kind": entry.kind, "name": entry.name},
            ),
            self._session,
        )

        return entry
