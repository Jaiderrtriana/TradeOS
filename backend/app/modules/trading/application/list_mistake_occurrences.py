"""
ListMistakeOccurrencesUseCase — a small, new, pure-read Use Case added in
Sprint 5.2: for every `trade_mistakes` row belonging to this user's
Trades, resolves the tagged Trade's `r_multiple` (via `compute_r_
multiple`, extracted from `Trade.r_multiple` this same sprint to avoid
duplicating the formula). `MistakePriorityRankingService`
(`app/modules/mistakes/domain/mistake_ranking.py`) needs exactly this —
added here, in Trading's own Application layer, rather than letting
Mistakes reach into Trading's repository directly
(`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3, Forbidden Dependencies), mirroring
`GetTradeByIdUseCase` (Sprint 5.1) and Configuration's `GetCatalogEntryUseCase`.

Returns `TradeMistakeCost`, a Trading-owned shape -- never `Mistakes`'
own domain type (`MistakeOccurrence`) -- so the dependency stays one-way
(Mistakes depends on Trading, never the reverse, per Backend Blueprint
§3.8: "Dependencies: Trading (read-only), Configuration (read-only)").
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import compute_r_multiple
from app.modules.trading.infrastructure.repository import TradeMistakeRepository


@dataclass(frozen=True)
class TradeMistakeCost:
    catalog_entry_id: uuid.UUID
    r_multiple: float | None


class ListMistakeOccurrencesUseCase:
    def __init__(self, trade_mistake_repository: TradeMistakeRepository) -> None:
        self._trade_mistakes = trade_mistake_repository

    async def execute(self, user_id: uuid.UUID) -> list[TradeMistakeCost]:
        facts = await self._trade_mistakes.list_trade_facts_for_ranking(user_id)
        return [
            TradeMistakeCost(
                catalog_entry_id=fact.catalog_entry_id,
                r_multiple=compute_r_multiple(
                    fact.direction, fact.entry_price, fact.stop_loss, fact.exit_price
                ),
            )
            for fact in facts
        ]


def build_list_mistake_occurrences_use_case(session: AsyncSession) -> ListMistakeOccurrencesUseCase:
    """Factory exposed so Mistakes' Application layer
    (`GetMistakeRankingUseCase`) can resolve mistake-tagged Trades' cost
    without ever importing Trading's infrastructure layer directly —
    same pattern as `build_get_trade_by_id_use_case`."""
    return ListMistakeOccurrencesUseCase(TradeMistakeRepository(session))
