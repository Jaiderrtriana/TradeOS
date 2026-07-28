"""
CloseTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.2;
`TRADEOS_API_SPECIFICATION.md` §6.4, `POST /trades/{id}/close`.

Business Flow (literal order from §4.2): validate `result`+`exit_price`
supplied together (INV-TRADE-02, already enforced by
`CloseTradeRequest`'s own required fields, re-validated here via the same
free function `Trade`/`AmendTrade` use, never duplicated) -> validate the
Trade is not already closed (`409`, state conflict) -> update Trade's
`result`/`exit_price`/`mfe_price`/`mae_price`/`closed_at` -> publish
`TradeClosed`.

`mfe_price`/`mae_price` are optional here ("this is the natural moment to
supply them since the trade's full excursion is now known," §6.4) — read
literally as *optional to supply now*, not *mandatory to have been null
before*: if omitted, whatever the Trade already carries (e.g. from
registration) is left untouched, never overwritten with `null`.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import (
    OPEN,
    Trade,
    validate_close_requires_result_and_exit_price,
)
from app.modules.trading.infrastructure.repository import TradeRepository
from app.platform.errors import ConflictError, NotFoundError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class CloseTradeUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._trades = trade_repository
        self._dispatcher = dispatcher
        self._session = session

    async def execute(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        result: str,
        exit_price: float,
        mfe_price: float | None = None,
        mae_price: float | None = None,
    ) -> Trade:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")
        if trade.result != OPEN:
            raise ConflictError("This trade is already closed.")

        trade.result = result
        trade.exit_price = exit_price
        if mfe_price is not None:
            trade.mfe_price = mfe_price
        if mae_price is not None:
            trade.mae_price = mae_price
        trade.closed_at = datetime.now(timezone.utc)

        validate_close_requires_result_and_exit_price(
            trade.result, trade.exit_price, trade.closed_at
        )

        trade.updated_at = datetime.now(timezone.utc)
        await self._trades.update(trade)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeClosed",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={"result": trade.result, "exit_price": trade.exit_price},
            ),
            self._session,
        )

        return trade
