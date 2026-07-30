"""
ListPlaybookSetupsUseCase — `TRADEOS_API_SPECIFICATION.md` §6.8,
`GET /playbook-setups`.

Deliberately does not compose Statistics -- the endpoint's own Notes
column is blank (unlike the detail endpoint's explicit "including live
performance"), and composing per-row would be an N+1 against Statistics
for no documented reason (Sprint 7.1 pre-analysis).
"""

from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.infrastructure.repository import (
    PlaybookSetupListCursor,
    PlaybookSetupRepository,
)


class ListPlaybookSetupsUseCase:
    def __init__(self, playbook_setup_repository: PlaybookSetupRepository) -> None:
        self._playbook_setups = playbook_setup_repository

    async def execute(
        self,
        *,
        sort_descending: bool = True,
        cursor: PlaybookSetupListCursor | None = None,
        limit: int = 50,
    ) -> list[PlaybookSetup]:
        return await self._playbook_setups.list_all(
            sort_descending=sort_descending, cursor=cursor, limit=limit
        )
