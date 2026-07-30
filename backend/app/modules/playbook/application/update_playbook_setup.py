"""
UpdatePlaybookSetupUseCase — `TRADEOS_API_SPECIFICATION.md` §6.8,
`PATCH /playbook-setups/{id}`: "Edit entry/exit criteria, ideal
conditions, risk rules."

Partial update -- API Spec's general PATCH rule (§3, "Partially update a
resource's mutable fields... applying the same patch twice yields the
same state"): only fields supplied (non-`None`) are overwritten. No
cross-field invariant exists for `PlaybookSetup` (unlike Trade's
INV-TRADE-01/02, which force a *full proposed state* re-validation on
`PATCH /trades/{id}`) -- the four text fields are mutually independent,
so a genuinely partial patch is safe here.

Publishes `PlaybookSetupUpdated` (`TRADEOS_BACKEND_BLUEPRINT.md` §3.7's
only named event for this module) -- "a setup's definition changed"
(Domain Model §11).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.infrastructure.repository import PlaybookSetupRepository
from app.platform.errors import NotFoundError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class UpdatePlaybookSetupUseCase:
    def __init__(
        self,
        playbook_setup_repository: PlaybookSetupRepository,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._playbook_setups = playbook_setup_repository
        self._dispatcher = dispatcher
        self._session = session

    async def execute(
        self,
        setup_id: uuid.UUID,
        entry_criteria: str | None = None,
        exit_criteria: str | None = None,
        ideal_conditions: str | None = None,
        risk_rules: str | None = None,
    ) -> PlaybookSetup:
        setup = await self._playbook_setups.get_by_id(setup_id)
        if setup is None:
            raise NotFoundError(f"No playbook setup with id '{setup_id}'.")

        changed_fields: list[str] = []
        if entry_criteria is not None and entry_criteria != setup.entry_criteria:
            setup.entry_criteria = entry_criteria
            changed_fields.append("entry_criteria")
        if exit_criteria is not None and exit_criteria != setup.exit_criteria:
            setup.exit_criteria = exit_criteria
            changed_fields.append("exit_criteria")
        if ideal_conditions is not None and ideal_conditions != setup.ideal_conditions:
            setup.ideal_conditions = ideal_conditions
            changed_fields.append("ideal_conditions")
        if risk_rules is not None and risk_rules != setup.risk_rules:
            setup.risk_rules = risk_rules
            changed_fields.append("risk_rules")

        setup.updated_at = datetime.now(timezone.utc)
        await self._playbook_setups.update(setup)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="PlaybookSetupUpdated",
                aggregate_type="PlaybookSetup",
                aggregate_id=setup.id,
                payload={"playbook_setup_id": str(setup.id), "changed_fields": changed_fields},
            ),
            self._session,
        )

        return setup
