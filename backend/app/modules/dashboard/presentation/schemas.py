"""
Dashboard presentation: Pydantic schemas for `GET /api/v1/dashboard`
(`TRADEOS_API_SPECIFICATION.md` §6.12).

`DashboardStatisticsSummaryResponse`/`DashboardRollingStatisticsResponse`/
`DashboardMistakeRankingEntryResponse` deliberately duplicate the field
sets already defined in `statistics.presentation.schemas`/
`mistakes.presentation.schemas` rather than importing them -- each
module owns its own HTTP contract DTOs (no cross-module
presentation-layer import), the same discipline
`playbook/presentation/schemas.py`'s own docstring already establishes
project-wide (Sprint 7.1): "each module owns its own HTTP contract
DTOs... applied everywhere in this project." The values themselves are
never recomputed here -- they are read straight off
`StatisticsSummary`/`RollingStatistics`/`MistakeRankingResult`, the
Application-layer dataclasses Statistics/Mistakes already compute
(`dashboard/application/get_dashboard.py`), so there is no risk of a
second, independent formula drifting from the first.

`DashboardTradeResponse` is Dashboard's own, deliberately lighter
projection of a Trade -- not `trading.presentation.schemas.
TradeSummaryResponse` -- because a Dashboard preview row needs less than
even the Trades List's own summary shape (no evaluation breakdown; a
trader drills into a row's full detail via Trade Detail, `TRADEOS_
FRONTEND_BLUEPRINT.md` §5.1: "navigate into any composed section's full
page").
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardStatisticsSummaryResponse(BaseModel):
    win_rate: float | None
    expectancy_r: float | None
    average_r: float | None
    profit_factor_r: float | None
    total_pnl: float
    average_confidence_score: float | None
    average_quality_score: float | None
    average_execution_score: float | None
    average_market_context_score: float | None
    average_bias_score: float | None


class DashboardRollingStatisticsResponse(BaseModel):
    window: int
    rolling: DashboardStatisticsSummaryResponse
    overall: DashboardStatisticsSummaryResponse


class DashboardMistakeRankingEntryResponse(BaseModel):
    catalog_entry_id: UUID
    name: str
    is_active: bool
    frequency: int
    total_cost_r: float | None
    priority: int


class DashboardTradeResponse(BaseModel):
    id: UUID
    market: str
    direction: str
    status: str
    result: str | None
    r_multiple: float | None
    entered_at: datetime | None


class DashboardResponse(BaseModel):
    overview: DashboardStatisticsSummaryResponse
    rolling: DashboardRollingStatisticsResponse
    top_mistakes: list[DashboardMistakeRankingEntryResponse]
    recent_trades: list[DashboardTradeResponse]
