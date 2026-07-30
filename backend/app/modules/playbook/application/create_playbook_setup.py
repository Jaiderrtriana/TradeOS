"""
CreatePlaybookSetupUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §3.7/§4.8;
`TRADEOS_API_SPECIFICATION.md` §6.8, `POST /playbook-setups`.

Business Flow (literal, §6.8): the referenced `CatalogEntry` must exist
and be `kind=setup` -> it must not already be linked to another Playbook
Setup (1:1) -> persist. Both checks return `422` per the endpoint's own
literal Notes column -- no `is_active` check exists in that citation
(Sprint 7.1 pre-analysis: deliberately not the same as
`TagMistakeUseCase`'s check, which does require an active tag).

`kind` is compared against the literal string `"setup"` rather than
importing Configuration's domain constant -- same structural-literal
precedent as `TagMistakeUseCase`'s own `MISTAKE_TAG = "mistake_tag"`
(Sprint 4.3).

The "already linked" check is an explicit pre-check via `PlaybookSetupRepository.
get_by_catalog_entry_id`, not an `IntegrityError` catch -- the literal
`422` (not `409`) the API Spec names for this case is a *known-in-advance*
rejection, not a race outcome; the schema's own `UNIQUE` constraint on
`catalog_entry_id` remains the concurrency backstop for a genuine race
(caught here as `IntegrityError` -> `ConflictError` on flush, mirroring
`TagMistakeUseCase`'s dual-layer pattern exactly).

No event published: `TRADEOS_DOMAIN_MODEL.md` §11 and Backend Blueprint
§3.7 name only `PlaybookSetupUpdated` -- no "Created" event exists for
Playbook anywhere (unlike Trading's `TradeRegistered`/`TradeAmended`
split), so none is invented here.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.infrastructure.repository import PlaybookSetupRepository
from app.platform.errors import ConflictError, UnprocessableEntityError

SETUP = "setup"


class CreatePlaybookSetupUseCase:
    def __init__(
        self,
        playbook_setup_repository: PlaybookSetupRepository,
        get_catalog_entry_use_case: GetCatalogEntryUseCase,
        session: AsyncSession,
    ) -> None:
        self._playbook_setups = playbook_setup_repository
        self._get_catalog_entry = get_catalog_entry_use_case
        self._session = session

    async def execute(
        self,
        catalog_entry_id: uuid.UUID,
        entry_criteria: str = "",
        exit_criteria: str = "",
        ideal_conditions: str = "",
        risk_rules: str = "",
    ) -> PlaybookSetup:
        entry = await self._get_catalog_entry.execute(catalog_entry_id)
        if entry is None or entry.kind != SETUP:
            raise UnprocessableEntityError(
                f"'{catalog_entry_id}' does not reference a setup catalog entry."
            )

        existing = await self._playbook_setups.get_by_catalog_entry_id(catalog_entry_id)
        if existing is not None:
            raise UnprocessableEntityError(
                f"Catalog entry '{catalog_entry_id}' is already linked to a Playbook Setup."
            )

        setup = PlaybookSetup(
            catalog_entry_id=catalog_entry_id,
            entry_criteria=entry_criteria,
            exit_criteria=exit_criteria,
            ideal_conditions=ideal_conditions,
            risk_rules=risk_rules,
        )
        await self._playbook_setups.add(setup)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                f"Catalog entry '{catalog_entry_id}' is already linked to a Playbook Setup."
            ) from exc
        return setup
