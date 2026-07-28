"""
DeleteTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.8's compact table
("DeleteTrade (soft) | Trading | none beyond ownership | none named — see
Open Question BE-2"); `TRADEOS_API_SPECIFICATION.md` §6.4,
`DELETE /trades/{id}`.

No event published — `TRADEOS_DOMAIN_MODEL.md` Section 11 names none for
Trade deletion, and Backend Blueprint §4.8 explicitly registers this as
Open Question BE-2 (Section 21: priority Low, impact Low) rather than
inventing one.

Idempotent (`TRADEOS_API_SPECIFICATION.md` §3.4: "`DELETE` ... Soft-delete
... Idempotent: Yes"): deleting an already-deleted Trade is a successful
no-op, never a 404 -- unlike every other Sprint 4.2 action, whose own
lookup treats an already-soft-deleted Trade as not-found. This is a
deliberate, narrow exception to that shared convention, not an
inconsistency: idempotency is what `DELETE`'s own HTTP semantics require.
"""

import uuid
from datetime import datetime, timezone

from app.modules.trading.infrastructure.repository import TradeRepository
from app.platform.errors import NotFoundError


class DeleteTradeUseCase:
    def __init__(self, trade_repository: TradeRepository) -> None:
        self._trades = trade_repository

    async def execute(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> None:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id:
            raise NotFoundError(f"No trade with id '{trade_id}'.")
        if trade.deleted_at is not None:
            return

        trade.deleted_at = datetime.now(timezone.utc)
        trade.updated_at = trade.deleted_at
        await self._trades.update(trade)
