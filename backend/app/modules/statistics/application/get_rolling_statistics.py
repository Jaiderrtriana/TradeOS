"""
GetRollingStatisticsUseCase -- `TRADEOS_BACKEND_BLUEPRINT.md` line 289's
compact row names it `GetRollingStatistics` (alongside `GetStatisticsOverview`/
`GetStatisticsByDimension`); `TRADEOS_API_SPECIFICATION.md` §6.10,
`GET /statistics/rolling?window=10|20|30|50|100|200`: "Same metrics,
computed over the most recent N Trades, alongside the all-time
comparison."

Pure orchestration -- no formula lives here (that's `aggregate_rolling`'s
job, `statistics/domain/statistics_aggregation.py`). Resolves every Trade
fact via Trading's own `ListTradeStatisticsFactsUseCase` factory (same
precedent as `GetStatisticsOverviewUseCase`/`GetStatisticsByDimensionUseCase`,
Sprint 6.1) -- never a repository directly.
"""

import uuid

from app.modules.statistics.application.mapping import to_statistics_fact
from app.modules.statistics.domain.statistics_aggregation import (
    RollingStatistics,
    aggregate_rolling,
)
from app.modules.trading.application.list_trade_statistics_facts import (
    ListTradeStatisticsFactsUseCase,
)


class GetRollingStatisticsUseCase:
    def __init__(
        self, list_trade_statistics_facts_use_case: ListTradeStatisticsFactsUseCase
    ) -> None:
        self._list_trade_statistics_facts = list_trade_statistics_facts_use_case

    async def execute(self, user_id: uuid.UUID, window: int) -> RollingStatistics:
        records = await self._list_trade_statistics_facts.execute(user_id)
        facts = [to_statistics_fact(record) for record in records]
        return aggregate_rolling(facts, window)
