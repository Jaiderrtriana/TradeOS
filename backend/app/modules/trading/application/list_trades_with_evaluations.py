"""
ListTradesWithEvaluationsUseCase — a small, new, pure-read Use Case
added in Sprint 8.1: pairs `ListTradesUseCase`'s already-existing
capability with each returned Trade's current `EvaluationSnapshot`
(`EvaluationSnapshotRepository.list_current_by_trade_ids`, the same
batched lookup `GET /trades` itself already performs) so a consumer
gets both in one call.

Added here, in Trading's own Application layer, so a cross-module
consumer (Dashboard, Sprint 8.1) can obtain this pairing without ever
importing Trading's `infrastructure/` directly (`TRADEOS_SYSTEM_
ARCHITECTURE.md` §3.3, Forbidden Dependencies) — same precedent as
`ListTradeStatisticsFactsUseCase` (Sprint 6.1) and
`ListMistakeOccurrencesUseCase` (Sprint 5.2).

Returns `Trade` and `EvaluationSnapshot` domain/read objects directly,
never a Pydantic response model — per the "each module owns its own
HTTP contract DTOs" discipline already established
(`playbook/presentation/schemas.py`'s own docstring, Sprint 7.1), a
consuming module's Presentation layer builds its own response shape
from these, exactly as `GetPlaybookSetupUseCase` already does with
Statistics' `StatisticsSummary`.

This is purely additive: `trading/presentation/router.py`'s own
`GET /trades` endpoint is unchanged and keeps its existing inline
composition — introducing this Use Case does not require touching
already-tested, working code.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.application.list_trades import ListTradesUseCase
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.repository import (
    EvaluationSnapshotRepository,
    TradeRepository,
)


@dataclass(frozen=True)
class TradeWithEvaluation:
    trade: Trade
    evaluation: EvaluationSnapshot | None


class ListTradesWithEvaluationsUseCase:
    def __init__(
        self,
        list_trades_use_case: ListTradesUseCase,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
    ) -> None:
        self._list_trades = list_trades_use_case
        self._evaluation_snapshots = evaluation_snapshot_repository

    async def execute(
        self,
        user_id: uuid.UUID,
        *,
        direction: str | None = None,
        status: str | None = None,
        result: str | None = None,
        entered_after: datetime | None = None,
        entered_before: datetime | None = None,
        strategy_id: uuid.UUID | None = None,
        setup_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        entry_trigger_id: uuid.UUID | None = None,
        sort_descending: bool = True,
        limit: int = 50,
    ) -> list[TradeWithEvaluation]:
        trades = await self._list_trades.execute(
            user_id,
            direction=direction,
            status=status,
            result=result,
            entered_after=entered_after,
            entered_before=entered_before,
            strategy_id=strategy_id,
            setup_id=setup_id,
            session_id=session_id,
            entry_trigger_id=entry_trigger_id,
            sort_descending=sort_descending,
            limit=limit,
        )
        snapshots_by_trade_id = await self._evaluation_snapshots.list_current_by_trade_ids(
            [trade.id for trade in trades]
        )
        return [
            TradeWithEvaluation(trade=trade, evaluation=snapshots_by_trade_id.get(trade.id))
            for trade in trades
        ]


def build_list_trades_with_evaluations_use_case(
    session: AsyncSession,
) -> ListTradesWithEvaluationsUseCase:
    """Factory exposed so a cross-module consumer (Dashboard's
    `GetDashboardUseCase`) can resolve recent Trades with their current
    Evaluation without ever importing Trading's infrastructure layer
    directly — same pattern as `build_list_trade_statistics_facts_use_case`."""
    return ListTradesWithEvaluationsUseCase(
        ListTradesUseCase(TradeRepository(session)),
        EvaluationSnapshotRepository(session),
    )
