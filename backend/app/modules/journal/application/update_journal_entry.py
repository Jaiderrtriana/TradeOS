"""
UpdateJournalEntryUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.8's compact
table row ("UpdateJournalEntry / DeleteJournalEntry (soft) | Journal |
reference type immutable after creation | none");
`TRADEOS_API_SPECIFICATION.md` §6.11, `PATCH /journal-entries/{id}`:
"Edit content (the reference type/target is immutable after creation —
changing what an entry is 'about' is modeled as delete-and-recreate, not
an edit, to avoid ambiguous history)." Only `content` is accepted here —
`trade_id`/`period_start`/`period_end` have no edit path at all, not even
one the request schema silently ignores.
"""

import uuid
from datetime import datetime, timezone

from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.repository import JournalEntryRepository
from app.platform.errors import NotFoundError


class UpdateJournalEntryUseCase:
    def __init__(self, journal_entry_repository: JournalEntryRepository) -> None:
        self._journal_entries = journal_entry_repository

    async def execute(self, entry_id: uuid.UUID, user_id: uuid.UUID, content: str) -> JournalEntry:
        entry = await self._journal_entries.get_by_id(entry_id)
        if entry is None or entry.user_id != user_id or entry.deleted_at is not None:
            raise NotFoundError(f"No journal entry with id '{entry_id}'.")

        entry.content = content
        entry.updated_at = datetime.now(timezone.utc)
        await self._journal_entries.update_content(entry)
        return entry
