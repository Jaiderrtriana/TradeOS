"""
DeleteJournalEntryUseCase — `TRADEOS_API_SPECIFICATION.md` §6.11,
`DELETE /journal-entries/{id}` (soft delete).

Idempotent (`TRADEOS_API_SPECIFICATION.md` §3.4: "`DELETE` ... Soft-delete
... Idempotent: Yes" — the same general HTTP-verb-semantics rule
`DeleteTradeUseCase` already applies): deleting an already-deleted entry
is a successful no-op, never a 404.
"""

import uuid
from datetime import datetime, timezone

from app.modules.journal.infrastructure.repository import JournalEntryRepository
from app.platform.errors import NotFoundError


class DeleteJournalEntryUseCase:
    def __init__(self, journal_entry_repository: JournalEntryRepository) -> None:
        self._journal_entries = journal_entry_repository

    async def execute(self, entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
        entry = await self._journal_entries.get_by_id(entry_id)
        if entry is None or entry.user_id != user_id:
            raise NotFoundError(f"No journal entry with id '{entry_id}'.")
        if entry.deleted_at is not None:
            return

        entry.deleted_at = datetime.now(timezone.utc)
        entry.updated_at = entry.deleted_at
        await self._journal_entries.soft_delete(entry)
