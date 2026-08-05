"""
CloseTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.2;
`TRADEOS_API_SPECIFICATION.md` §6.4, `POST /trades/{id}/close`.

Business Flow (literal order from §4.2): validate the Trade is `Open`
(`409` Conflict otherwise — INV-TRADE-04: a `Planned` Trade must call
`open` first; an already-`Closed` Trade rejects outright, closing is not
idempotent) -> update Trade's `status`/`result`/`exit_price`/
`realized_pnl`/`closed_at`/`mfe_price`/`mae_price` -> re-validate
INV-TRADE-02 via the same `validate_status_fields` free function every
other write path uses, never duplicated -> publish `TradeClosed`.

v2.0 (Trade Entry redesign, Domain Model KDD-07): `realized_pnl` and
`closed_at` are now trader-supplied request fields (e.g. from the
exchange / the trader's own record of when they closed) — the exact same
"never derive what can't be derived" reasoning as `roi_percent`/
`pnl_percent` staying computed-only, but in the opposite direction:
`realized_pnl` genuinely cannot be derived from price/size alone (fees,
funding are not captured), so it must be supplied, not computed.
`closed_at` is no longer set to `now()` server-side — a `Closed` Trade
can be entered retroactively (backfilling historical trades) with its
real close timestamp.

`mfe_price`/`mae_price` are optional here ("this is the natural moment to
supply them since the trade's full excursion is now known," §6.4) — read
literally as *optional to supply now*, not *mandatory to have been null
before*: if omitted, whatever the Trade already carries (e.g. from
registration) is left untouched, never overwritten with `null`.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import CLOSED, OPEN, Trade, validate_status_fields
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
        realized_pnl: float,
        closed_at: datetime,
        mfe_price: float | None = None,
        mae_price: float | None = None,
    ) -> Trade:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")
        if trade.status != OPEN:
            raise ConflictError("This trade is not open.")

        trade.status = CLOSED
        trade.result = result
        trade.exit_price = exit_price
        trade.realized_pnl = realized_pnl
        trade.closed_at = closed_at
        if mfe_price is not None:
            trade.mfe_price = mfe_price
        if mae_price is not None:
            trade.mae_price = mae_price

        validate_status_fields(
            trade.status,
            trade.entry_price,
            trade.entered_at,
            trade.exit_price,
            trade.closed_at,
            trade.result,
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
