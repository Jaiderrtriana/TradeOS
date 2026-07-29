"""
GetStatisticsOverviewUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.8's
compact row ("GetStatisticsOverview... | Statistics | none (pure read) |
none"); `TRADEOS_API_SPECIFICATION.md` §6.10, `GET /statistics/overview`.

Pure orchestration -- no formula lives here. Resolves every Trade fact
via Trading's own `ListTradeStatisticsFactsUseCase` factory (never a
repository directly, `TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3), converts
each into `StatisticsFact` (this module's own domain input shape), and
delegates the actual computation to `aggregate_statistics`.
"""

import uuid

from app.modules.statistics.application.mapping import to_statistics_fact
from app.modules.statistics.domain.statistics_aggregation import (
    StatisticsSummary,
    aggregate_statistics,
)
from app.modules.trading.application.list_trade_statistics_facts import (
    ListTradeStatisticsFactsUseCase,
)


class GetStatisticsOverviewUseCase:
    def __init__(
        self, list_trade_statistics_facts_use_case: ListTradeStatisticsFactsUseCase
    ) -> None:
        self._list_trade_statistics_facts = list_trade_statistics_facts_use_case

    async def execute(self, user_id: uuid.UUID) -> StatisticsSummary:
        records = await self._list_trade_statistics_facts.execute(user_id)
        facts = [to_statistics_fact(record) for record in records]
        return aggregate_statistics(facts)
