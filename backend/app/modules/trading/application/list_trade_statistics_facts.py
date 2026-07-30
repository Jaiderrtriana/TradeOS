"""
ListTradeStatisticsFactsUseCase — a small, new, pure-read Use Case added
in Sprint 6.1: for every one of this user's non-deleted Trades, resolves
`r_multiple` (via `compute_r_multiple`, Sprint 5.2) and the current
Evaluation Snapshot's five engine scores (via `EvaluationSnapshotRepository.
list_current_by_trade_ids`, Sprint 4.1 — reused unchanged, never
duplicated). `StatisticsAggregationService` (`app/modules/statistics/
domain/statistics_aggregation.py`) needs exactly this — added here, in
Trading's own Application layer, rather than letting Statistics reach
into Trading's repositories directly (`TRADEOS_SYSTEM_ARCHITECTURE.md`
§3.3, Forbidden Dependencies), mirroring `ListMistakeOccurrencesUseCase`
(Sprint 5.2) and `GetTradeByIdUseCase` (Sprint 5.1).

Returns `TradeStatisticsRecord`, a Trading-owned shape -- never
Statistics' own domain type -- so the dependency stays one-way
(Statistics depends on Trading, never the reverse, per Backend Blueprint
§3.9: "Dependencies: Trading, Evaluation (both read-only)" -- Evaluation
data is read here via Trading's own `EvaluationSnapshotRepository`,
which already lives in `trading/infrastructure/`, since `evaluation_
snapshots` is a `trading`-schema table, not a separate module read).

Two queries total, never N+1: one for every Trade's raw facts
(`TradeRepository.list_all_facts_for_statistics`), one batched read for
every one of those Trades' current Evaluation Snapshot.

`entered_at` (Sprint 6.2) passes through unchanged -- Rolling Statistics
needs it to select "the most recent N Trades" (`TRADEOS_DOMAIN_MODEL.md`
§2.3); Overview/By-Dimension simply ignore the field, same as they
already ignore `id`.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.trade import compute_r_multiple
from app.modules.trading.infrastructure.repository import (
    EvaluationSnapshotRepository,
    TradeRepository,
)


@dataclass(frozen=True)
class TradeStatisticsRecord:
    id: uuid.UUID
    direction: str
    result: str
    realized_pnl: float
    r_multiple: float | None
    strategy_id: uuid.UUID | None
    setup_id: uuid.UUID | None
    session_id: uuid.UUID | None
    entered_at: datetime
    confidence_score: float | None
    quality_score: float | None
    execution_score: float | None
    market_context_score: float | None
    bias_score: float | None


class ListTradeStatisticsFactsUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
    ) -> None:
        self._trades = trade_repository
        self._evaluation_snapshots = evaluation_snapshot_repository

    async def execute(self, user_id: uuid.UUID) -> list[TradeStatisticsRecord]:
        facts = await self._trades.list_all_facts_for_statistics(user_id)
        snapshots_by_trade_id = await self._evaluation_snapshots.list_current_by_trade_ids(
            [fact.id for fact in facts]
        )

        records: list[TradeStatisticsRecord] = []
        for fact in facts:
            snapshot = snapshots_by_trade_id.get(fact.id)
            records.append(
                TradeStatisticsRecord(
                    id=fact.id,
                    direction=fact.direction,
                    result=fact.result,
                    realized_pnl=fact.realized_pnl,
                    r_multiple=compute_r_multiple(
                        fact.direction, fact.entry_price, fact.stop_loss, fact.exit_price
                    ),
                    strategy_id=fact.strategy_id,
                    setup_id=fact.setup_id,
                    session_id=fact.session_id,
                    entered_at=fact.entered_at,
                    confidence_score=snapshot.confidence_score if snapshot else None,
                    quality_score=snapshot.quality_score if snapshot else None,
                    execution_score=snapshot.execution_score if snapshot else None,
                    market_context_score=snapshot.market_context_score if snapshot else None,
                    bias_score=snapshot.bias_score if snapshot else None,
                )
            )
        return records


def build_list_trade_statistics_facts_use_case(
    session: AsyncSession,
) -> ListTradeStatisticsFactsUseCase:
    """Factory exposed so Statistics' Application layer
    (`GetStatisticsOverviewUseCase`/`GetStatisticsByDimensionUseCase`)
    can resolve every Trade fact it needs without ever importing
    Trading's infrastructure layer directly — same pattern as
    `build_list_mistake_occurrences_use_case`."""
    return ListTradeStatisticsFactsUseCase(
        TradeRepository(session), EvaluationSnapshotRepository(session)
    )
