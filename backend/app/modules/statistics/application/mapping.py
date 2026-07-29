"""Shared conversion between Trading's own application-layer shape
(`TradeStatisticsRecord`) and Statistics' domain input shape
(`StatisticsFact`) — used by both `GetStatisticsOverviewUseCase` and
`GetStatisticsByDimensionUseCase`, kept in one place rather than
duplicated across the two."""

from app.modules.statistics.domain.statistics_aggregation import StatisticsFact
from app.modules.trading.application.list_trade_statistics_facts import TradeStatisticsRecord


def to_statistics_fact(record: TradeStatisticsRecord) -> StatisticsFact:
    return StatisticsFact(
        result=record.result,
        realized_pnl=record.realized_pnl,
        r_multiple=record.r_multiple,
        strategy_id=record.strategy_id,
        setup_id=record.setup_id,
        session_id=record.session_id,
        direction=record.direction,
        confidence_score=record.confidence_score,
        quality_score=record.quality_score,
        execution_score=record.execution_score,
        market_context_score=record.market_context_score,
        bias_score=record.bias_score,
    )
