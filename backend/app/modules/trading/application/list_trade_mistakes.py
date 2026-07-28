"""
ListTradeMistakesUseCase — `TRADEOS_API_SPECIFICATION.md` §6.4,
`GET /trades/{id}/mistakes`: every Mistake Tag currently attached to a
Trade. Closed alongside the rest of Sprint 4.4's read-endpoint gaps, by
the same reasoning as the earlier `GET /trades`/`GET /trades/{id}` work:
Trade Detail's Mistakes section cannot show what's already tagged
without it. Pure read — no new business logic, no change to
`TagMistakeUseCase`'s already-approved write behavior.
"""

import uuid

from app.modules.trading.domain.trade_mistake import TradeMistake
from app.modules.trading.infrastructure.repository import TradeMistakeRepository, TradeRepository
from app.platform.errors import NotFoundError


class ListTradeMistakesUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        trade_mistake_repository: TradeMistakeRepository,
    ) -> None:
        self._trades = trade_repository
        self._trade_mistakes = trade_mistake_repository

    async def execute(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> list[TradeMistake]:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        return await self._trade_mistakes.list_by_trade_id(trade_id)
