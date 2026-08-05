"""
GetDashboardUseCase — `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §9,
Sprint 8.1: "GET /dashboard, composing already-built Trades + Statistics
capability... introduces no new backend logic."
`TRADEOS_API_SPECIFICATION.md` §5.1/§6.12: a single composition endpoint,
never its own Bounded Context, owning no data of its own.

Pure orchestration, same shape as `GetPlaybookSetupUseCase` (Sprint
7.1): every section is resolved by calling the owning module's own
Application-layer Use Case through its public factory — never a
repository directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3). No formula,
no aggregation, and no new Domain Invariant lives here; every number
already comes computed from Statistics/Mistakes/Trading.

Extensibility (deliberately, per Sprint 8.1 scope): `DashboardSummary`
holds one field per composed section, and `execute()` resolves each
field with its own independent call. Adding a future composed section
(e.g. Equity Curve, Playbook Performance, Market Bias — all currently
unbuilt/reserved, `TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §17) means
adding one more field and one more call here, never restructuring the
sections that already exist. No registry, no plugin mechanism, no
speculative abstraction beyond this — none of those future sections has
a confirmed Domain Model entity or endpoint today, so none is stubbed.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mistakes.application.get_mistake_ranking import (
    GetMistakeRankingUseCase,
    MistakeRankingResult,
)
from app.modules.configuration.application.list_catalog_entries import (
    build_list_catalog_entries_use_case,
)
from app.modules.statistics.application.get_rolling_statistics import (
    GetRollingStatisticsUseCase,
)
from app.modules.statistics.application.get_statistics_overview import (
    GetStatisticsOverviewUseCase,
)
from app.modules.statistics.domain.statistics_aggregation import (
    RollingStatistics,
    StatisticsSummary,
)
from app.modules.trading.application.list_mistake_occurrences import (
    build_list_mistake_occurrences_use_case,
)
from app.modules.trading.application.list_trade_statistics_facts import (
    build_list_trade_statistics_facts_use_case,
)
from app.modules.trading.application.list_trades_with_evaluations import (
    ListTradesWithEvaluationsUseCase,
    TradeWithEvaluation,
    build_list_trades_with_evaluations_use_case,
)

# `TRADEOS_FRONTEND_BLUEPRINT.md` §5.1: "a Mistakes ranking preview
# (top 3)" -- the only one of the four sections with an explicit number
# in a frozen document.
TOP_MISTAKES_LIMIT = 3

# No frozen document names a count for "a recent Trades list preview"
# (`TRADEOS_API_SPECIFICATION.md` §6.12: "the most recent few Trades").
# Approved resolution (Sprint 8.1 pre-analysis, confirmed by product
# owner): 5, the same order of magnitude as the Mistakes preview above.
RECENT_TRADES_LIMIT = 5

# No frozen document names a numeric default `window` for Rolling
# Statistics in this composition (`TRADEOS_API_SPECIFICATION.md` §6.12
# only says "default window"). Approved resolution (Sprint 8.1
# pre-analysis, confirmed by product owner): 10 -- the same value
# `frontend/src/features/statistics/components/RollingTab.tsx` already
# uses as its own initial `useState<RollingWindow>(10)`.
DEFAULT_ROLLING_WINDOW = 10


@dataclass(frozen=True)
class DashboardSummary:
    overview: StatisticsSummary
    rolling: RollingStatistics
    top_mistakes: list[MistakeRankingResult]
    recent_trades: list[TradeWithEvaluation]


class GetDashboardUseCase:
    def __init__(
        self,
        get_statistics_overview_use_case: GetStatisticsOverviewUseCase,
        get_rolling_statistics_use_case: GetRollingStatisticsUseCase,
        get_mistake_ranking_use_case: GetMistakeRankingUseCase,
        list_trades_with_evaluations_use_case: ListTradesWithEvaluationsUseCase,
    ) -> None:
        self._get_overview = get_statistics_overview_use_case
        self._get_rolling = get_rolling_statistics_use_case
        self._get_mistake_ranking = get_mistake_ranking_use_case
        self._list_trades_with_evaluations = list_trades_with_evaluations_use_case

    async def execute(self, user_id: uuid.UUID) -> DashboardSummary:
        overview = await self._get_overview.execute(user_id)
        rolling = await self._get_rolling.execute(user_id, DEFAULT_ROLLING_WINDOW)
        mistakes = await self._get_mistake_ranking.execute(user_id)
        recent_trades = await self._list_trades_with_evaluations.execute(
            user_id, sort_descending=True, limit=RECENT_TRADES_LIMIT
        )
        return DashboardSummary(
            overview=overview,
            rolling=rolling,
            top_mistakes=mistakes[:TOP_MISTAKES_LIMIT],
            recent_trades=recent_trades,
        )


def build_get_dashboard_use_case(session: AsyncSession) -> GetDashboardUseCase:
    """Factory so the Presentation layer never constructs a dependency
    chain by hand -- same discipline as every other module's `build_*`
    factory (`build_list_trade_statistics_facts_use_case`,
    `build_list_mistake_occurrences_use_case`,
    `build_list_catalog_entries_use_case`,
    `build_list_trades_with_evaluations_use_case`). The router obtains a
    fully-wired `GetDashboardUseCase` from this single call and invokes
    it -- it never builds `GetStatisticsOverviewUseCase`,
    `GetRollingStatisticsUseCase`, `GetMistakeRankingUseCase`, or
    `ListTradesWithEvaluationsUseCase` itself."""
    list_trade_statistics_facts_use_case = build_list_trade_statistics_facts_use_case(session)
    return GetDashboardUseCase(
        get_statistics_overview_use_case=GetStatisticsOverviewUseCase(
            list_trade_statistics_facts_use_case
        ),
        get_rolling_statistics_use_case=GetRollingStatisticsUseCase(
            list_trade_statistics_facts_use_case
        ),
        get_mistake_ranking_use_case=GetMistakeRankingUseCase(
            build_list_mistake_occurrences_use_case(session),
            build_list_catalog_entries_use_case(session),
        ),
        list_trades_with_evaluations_use_case=build_list_trades_with_evaluations_use_case(session),
    )
