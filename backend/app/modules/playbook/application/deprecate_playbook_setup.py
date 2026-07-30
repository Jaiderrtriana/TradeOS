"""
DeprecatePlaybookSetupUseCase — `TRADEOS_API_SPECIFICATION.md` §6.8,
`POST /playbook-setups/{id}/deprecate`: "Mark as no longer actively
traded... retained for historical attribution."

Domain Model §13.4's lifecycle is `( Active ) -> ( Deprecated )` with no
reverse transition and no third state -- deprecating an already-deprecated
setup is rejected as a state conflict (`409`), same convention
`CloseTradeUseCase` already applies to closing an already-closed Trade.

Never touches the linked `CatalogEntry`'s own `is_active` flag -- Playbook
and Configuration are separate lifecycles (Domain Model §11's Domain
Events table lists `PlaybookSetupUpdated` and `CatalogEntryDeactivated`
as distinct events with distinct triggers), and the architecture forbids
Playbook from writing into Configuration in any case (`TRADEOS_SYSTEM_
ARCHITECTURE.md` §3.3).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playbook.domain.playbook_setup import DEPRECATED, PlaybookSetup
from app.modules.playbook.infrastructure.repository import PlaybookSetupRepository
from app.platform.errors import ConflictError, NotFoundError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class DeprecatePlaybookSetupUseCase:
    def __init__(
        self,
        playbook_setup_repository: PlaybookSetupRepository,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._playbook_setups = playbook_setup_repository
        self._dispatcher = dispatcher
        self._session = session

    async def execute(self, setup_id: uuid.UUID) -> PlaybookSetup:
        setup = await self._playbook_setups.get_by_id(setup_id)
        if setup is None:
            raise NotFoundError(f"No playbook setup with id '{setup_id}'.")
        if setup.status == DEPRECATED:
            raise ConflictError("This playbook setup is already deprecated.")

        setup.status = DEPRECATED
        setup.updated_at = datetime.now(timezone.utc)
        await self._playbook_setups.update(setup)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="PlaybookSetupUpdated",
                aggregate_type="PlaybookSetup",
                aggregate_id=setup.id,
                payload={"playbook_setup_id": str(setup.id), "status": DEPRECATED},
            ),
            self._session,
        )

        return setup
