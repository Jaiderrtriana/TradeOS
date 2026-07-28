"""
AmendTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.8's compact table
("AmendTrade | Trading | INV-TRADE-01/02 re-validated against proposed
full state | TradeAmended"); `TRADEOS_API_SPECIFICATION.md` §6.4,
`PATCH /trades/{id}`.

Field set (approved, Sprint 4.2): every Trade fact **except**
`result`/`exit_price`/`closed_at` — those three stay `CloseTrade`'s
exclusive responsibility. Two independent citations support this split:
the lifecycle diagram (`TRADEOS_DOMAIN_MODEL.md` §13.1) only ever draws
`Open──amend──▶Open` and `Closed──amend──▶Closed` — never
`Open──amend──▶Closed` — and API Specification §3.5 states the general
design rule directly: *"`POST /trades/{id}/close` — not `PATCH
/trades/{id}` with `result` in the body — because closing enforces...
`TradeClosed`."* `checklist_answers` is likewise never amendable here —
`ReevaluateTrade` (§4.3) explicitly reloads the existing `ChecklistSnapshot`
"(unchanged)," confirming it has no PATCH-style edit path of its own.

"Re-validated against the proposed full state, not just the changed
field" (§4.8): `changes` is applied onto the already-loaded `Trade`
before either `validate_stop_placement`/`validate_close_requires_result_
and_exit_price` runs — the same two free functions `Trade.__post_init__`
itself calls at construction time, reused here rather than duplicated,
so amendment and registration can never silently diverge on what counts
as a valid Trade state.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import (
    Trade,
    validate_close_requires_result_and_exit_price,
    validate_stop_placement,
)
from app.modules.trading.infrastructure.repository import TradeRepository
from app.platform.errors import NotFoundError, UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher

# The complete amendable field set -- deliberately excludes result,
# exit_price, closed_at (CloseTrade's own responsibility, see module
# docstring), plus id/user_id/timestamps/realized_pnl/created_by_user_id
# (none of which any frozen document names as amendable).
AMENDABLE_FIELDS = frozenset(
    {
        "market",
        "direction",
        "entry_price",
        "stop_loss",
        "size",
        "leverage",
        "notes",
        "strategy_id",
        "setup_id",
        "session_id",
        "entry_trigger_id",
        "mfe_price",
        "mae_price",
    }
)


class AmendTradeUseCase:
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
        self, trade_id: uuid.UUID, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Trade:
        trade = await self._trades.get_by_id(trade_id)
        # Not found, not owned, and soft-deleted all return the same 404
        # -- ownership is never leaked by a different error shape
        # (`TRADEOS_API_SPECIFICATION.md` §14, already the convention for
        # GET /trades/{id}); a soft-deleted Trade behaves as not-found for
        # every write action except DeleteTrade's own idempotent retry.
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        # Defense in depth: AmendTradeRequest's own field set already
        # excludes result/exit_price/closed_at (see module docstring), so
        # this can only trip if some future, non-HTTP caller bypasses that
        # schema -- the Use Case's own contract shouldn't rely solely on
        # the presentation layer to hold the line.
        disallowed = set(changes.keys()) - AMENDABLE_FIELDS
        if disallowed:
            raise UnprocessableEntityError(f"Cannot amend field(s): {sorted(disallowed)}.")

        for field, value in changes.items():
            setattr(trade, field, value)

        validate_stop_placement(trade.direction, trade.entry_price, trade.stop_loss)
        validate_close_requires_result_and_exit_price(
            trade.result, trade.exit_price, trade.closed_at
        )

        trade.updated_at = datetime.now(timezone.utc)
        await self._trades.update(trade)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeAmended",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={"changed_fields": sorted(changes.keys())},
            ),
            self._session,
        )

        return trade
