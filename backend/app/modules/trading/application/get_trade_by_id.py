"""
GetTradeByIdUseCase — a small, new, pure-read Use Case added in Sprint
5.1: resolves a single `Trade` by id, with no bundled Checklist/
Evaluation data. `GetTradeUseCase` (`get_trade.py`) already covers
`GET /trades/{id}`'s own full presentation need, but `CreateJournalEntryUseCase`
(`app/modules/journal/application/create_journal_entry.py`) only needs
to validate that a supplied `trade_id` exists and is owned by the caller
(`TRADEOS_BACKEND_BLUEPRINT.md` §3.10) — added here, in Trading's own
Application layer, rather than letting Journal reach into Trading's
repository directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3, Forbidden
Dependencies), mirroring Configuration's `GetCatalogEntryUseCase`
(`get_catalog_entry.py`)'s own cross-module factory precedent.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.repository import TradeRepository


class GetTradeByIdUseCase:
    def __init__(self, trade_repository: TradeRepository) -> None:
        self._trades = trade_repository

    async def execute(self, trade_id: uuid.UUID) -> Trade | None:
        return await self._trades.get_by_id(trade_id)


def build_get_trade_by_id_use_case(session: AsyncSession) -> GetTradeByIdUseCase:
    """Factory exposed so Journal's Application layer
    (`CreateJournalEntryUseCase`) can resolve a Trade without ever
    importing Trading's infrastructure layer directly — same pattern as
    `build_get_catalog_entry_use_case`."""
    return GetTradeByIdUseCase(TradeRepository(session))
