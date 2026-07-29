"""
CreateJournalEntryUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.7;
`TRADEOS_API_SPECIFICATION.md` §6.11, `POST /journal-entries`.

Business Flow (§4.7, literal): "validate the exactly-one-reference rule
-> persist the entry." The exactly-one-reference check itself lives in
`JournalEntry.__post_init__` (domain layer, `validate_exactly_one_
reference`) — this Use Case's own job is the one precondition the domain
object cannot check by itself: "if `trade_id` is supplied, it must be
owned by the caller" (§4.7's Preconditions), via Trading's own
`GetTradeByIdUseCase` factory (Journal's only cross-module dependency,
per Backend Blueprint §3.10: "Dependencies: Trading (validates a
supplied `trade_id` exists and is owned by the caller)") — never
Trading's repository directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3),
same discipline `RegisterTradeUseCase` already applies to Configuration.

No event published (`TRADEOS_DOMAIN_MODEL.md` §11 names none for
Journal — confirmed absent, not an oversight, per Backend Blueprint
§4.7's own docstring).
"""

import uuid
from datetime import date

from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.repository import JournalEntryRepository
from app.modules.trading.application.get_trade_by_id import GetTradeByIdUseCase
from app.platform.errors import NotFoundError


class CreateJournalEntryUseCase:
    def __init__(
        self,
        journal_entry_repository: JournalEntryRepository,
        get_trade_by_id_use_case: GetTradeByIdUseCase,
    ) -> None:
        self._journal_entries = journal_entry_repository
        self._get_trade_by_id = get_trade_by_id_use_case

    async def execute(
        self,
        user_id: uuid.UUID,
        content: str,
        trade_id: uuid.UUID | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> JournalEntry:
        if trade_id is not None:
            trade = await self._get_trade_by_id.execute(trade_id)
            # Not found, not owned, and soft-deleted all return the same
            # 404 -- same ownership-leak-avoidance convention every other
            # Trading-referencing write already applies.
            if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
                raise NotFoundError(f"No trade with id '{trade_id}'.")

        # JournalEntry.__post_init__ enforces the exactly-one-reference
        # rule itself -- constructing it is where that validation runs.
        entry = JournalEntry(
            user_id=user_id,
            content=content,
            trade_id=trade_id,
            period_start=period_start,
            period_end=period_end,
        )
        await self._journal_entries.add(entry)
        return entry
