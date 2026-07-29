"""
ListJournalEntriesUseCase — `TRADEOS_API_SPECIFICATION.md` §6.11,
`GET /journal-entries`: "filterable by `trade_id` or a date range
overlapping `period_start`/`period_end`."
"""

import uuid
from datetime import date

from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.repository import (
    JournalEntryListCursor,
    JournalEntryRepository,
)


class ListJournalEntriesUseCase:
    def __init__(self, journal_entry_repository: JournalEntryRepository) -> None:
        self._journal_entries = journal_entry_repository

    async def execute(
        self,
        user_id: uuid.UUID,
        *,
        trade_id: uuid.UUID | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        sort_descending: bool = True,
        cursor: JournalEntryListCursor | None = None,
        limit: int = 50,
    ) -> list[JournalEntry]:
        return await self._journal_entries.list_all(
            user_id=user_id,
            trade_id=trade_id,
            period_start=period_start,
            period_end=period_end,
            sort_descending=sort_descending,
            cursor=cursor,
            limit=limit,
        )
