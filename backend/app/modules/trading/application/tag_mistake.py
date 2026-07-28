"""
TagMistakeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.6;
`TRADEOS_API_SPECIFICATION.md` §6.4, `POST /trades/{id}/mistakes`.

Business Flow (literal order from §4.6): the Trade is owned by the caller
(and not soft-deleted -- same convention as every Sprint 4.2 write
action) -> the referenced `CatalogEntry` exists, is `kind=mistake_tag`,
and is active -> insert a `trade_mistakes` row -> publish `MistakeTagged`.

`kind` is compared against the literal string `"mistake_tag"` rather than
importing Configuration's `MISTAKE_TAG` domain constant --
`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3 (never import another module's
domain layer directly). Same structural-literal precedent as
`reevaluate_trade.py`'s own `PUBLISHED = "published"`; the value itself
is a stable wire value fixed by `TRADEOS_DATABASE_DESIGN.md` §6.8's own
`kind` column values, not an implementation detail that could drift.

Duplicate tagging (approved, Sprint 4.3): the composite primary key
`(trade_id, catalog_entry_id)` is the concurrency-safety mechanism —
`TradeMistakeRepository.add()` never checks existence first, it just
attempts the insert; `IntegrityError` on flush is translated to
`ConflictError` (409) here, mirroring
`PublishScoringConfigurationVersionUseCase`'s own `IntegrityError` ->
`ConflictError` translation.

No Open/Closed precondition on the Trade's own `result`: DB Design
§6.14 explicitly registers this as unresolved (Open Question DB-2, Low
priority) -- "not blocked at the database level" -- and Backend
Blueprint §4.6 names no such precondition either. Not invented here.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.trading.domain.trade_mistake import TradeMistake
from app.modules.trading.infrastructure.repository import TradeMistakeRepository, TradeRepository
from app.platform.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher

MISTAKE_TAG = "mistake_tag"


class TagMistakeUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        trade_mistake_repository: TradeMistakeRepository,
        get_catalog_entry_use_case: GetCatalogEntryUseCase,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._trades = trade_repository
        self._trade_mistakes = trade_mistake_repository
        self._get_catalog_entry = get_catalog_entry_use_case
        self._dispatcher = dispatcher
        self._session = session

    async def execute(
        self, trade_id: uuid.UUID, user_id: uuid.UUID, catalog_entry_id: uuid.UUID
    ) -> TradeMistake:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        entry = await self._get_catalog_entry.execute(catalog_entry_id)
        if entry is None or entry.kind != MISTAKE_TAG or not entry.is_active:
            raise UnprocessableEntityError(
                f"'{catalog_entry_id}' does not reference an active mistake tag."
            )

        trade_mistake = TradeMistake(trade_id=trade_id, catalog_entry_id=catalog_entry_id)
        await self._trade_mistakes.add(trade_mistake)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("This mistake is already tagged on this trade.") from exc

        await self._dispatcher.publish(
            DomainEvent(
                event_type="MistakeTagged",
                aggregate_type="Trade",
                aggregate_id=trade_id,
                payload={"catalog_entry_id": str(catalog_entry_id)},
            ),
            self._session,
        )

        return trade_mistake
