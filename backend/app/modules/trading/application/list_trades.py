"""
ListTradesUseCase — `TRADEOS_API_SPECIFICATION.md` §6.4, `GET /trades`;
filtering/sorting/pagination contract per §7. Pure read, no business
logic beyond the ownership/soft-delete scoping `TradeRepository.list_all`
already applies (see that method's own docstring for the keyset-
pagination and sort-field rationale).
"""

import uuid
from datetime import datetime

from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.repository import TradeListCursor, TradeRepository


class ListTradesUseCase:
    def __init__(self, trade_repository: TradeRepository) -> None:
        self._trades = trade_repository

    async def execute(
        self,
        user_id: uuid.UUID,
        *,
        direction: str | None = None,
        result: str | None = None,
        entered_after: datetime | None = None,
        entered_before: datetime | None = None,
        strategy_id: uuid.UUID | None = None,
        setup_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        entry_trigger_id: uuid.UUID | None = None,
        sort_descending: bool = True,
        cursor: TradeListCursor | None = None,
        limit: int = 50,
    ) -> list[Trade]:
        return await self._trades.list_all(
            user_id=user_id,
            direction=direction,
            result=result,
            entered_after=entered_after,
            entered_before=entered_before,
            strategy_id=strategy_id,
            setup_id=setup_id,
            session_id=session_id,
            entry_trigger_id=entry_trigger_id,
            sort_descending=sort_descending,
            cursor=cursor,
            limit=limit,
        )
