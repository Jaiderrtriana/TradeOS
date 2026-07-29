"""
GetJournalEntryUseCase — `TRADEOS_API_SPECIFICATION.md` §6.11,
`GET /journal-entries/{id}`.
"""

import uuid

from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.repository import JournalEntryRepository
from app.platform.errors import NotFoundError


class GetJournalEntryUseCase:
    def __init__(self, journal_entry_repository: JournalEntryRepository) -> None:
        self._journal_entries = journal_entry_repository

    async def execute(self, entry_id: uuid.UUID, user_id: uuid.UUID) -> JournalEntry:
        entry = await self._journal_entries.get_by_id(entry_id)
        # Not found, not owned, and soft-deleted all return the same 404
        # -- `TRADEOS_API_SPECIFICATION.md` §8: "a resource that exists
        # but isn't owned by the caller returns 404, not 403, for
        # Trades/JournalEntries specifically."
        if entry is None or entry.user_id != user_id or entry.deleted_at is not None:
            raise NotFoundError(f"No journal entry with id '{entry_id}'.")
        return entry
