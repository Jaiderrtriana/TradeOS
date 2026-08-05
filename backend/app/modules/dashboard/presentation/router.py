"""
Dashboard presentation: `GET /api/v1/dashboard` — `TRADEOS_API_
SPECIFICATION.md` §6.12. Read-only; no write endpoint exists in this
module (Dashboard is a composition, never a Bounded Context, §5.1).

No pagination envelope, no query parameters -- a bare JSON object, same
precedent as `GET /statistics/overview`/`GET /mistakes/ranking`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.application.get_dashboard import (
    DashboardSummary,
    build_get_dashboard_use_case,
)
from app.modules.dashboard.presentation.schemas import (
    DashboardMistakeRankingEntryResponse,
    DashboardResponse,
    DashboardRollingStatisticsResponse,
    DashboardStatisticsSummaryResponse,
    DashboardTradeResponse,
)
from app.modules.mistakes.application.get_mistake_ranking import MistakeRankingResult
from app.modules.statistics.domain.statistics_aggregation import (
    RollingStatistics,
    StatisticsSummary,
)
from app.modules.trading.application.list_trades_with_evaluations import TradeWithEvaluation
from app.platform.db.session import get_db_session
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> DashboardResponse:
    use_case = build_get_dashboard_use_case(session)
    summary = await use_case.execute(user_id)
    return _dashboard_response(summary)


def _dashboard_response(summary: DashboardSummary) -> DashboardResponse:
    return DashboardResponse(
        overview=_summary_response(summary.overview),
        rolling=_rolling_response(summary.rolling),
        top_mistakes=[_mistake_response(entry) for entry in summary.top_mistakes],
        recent_trades=[_trade_response(entry) for entry in summary.recent_trades],
    )


def _summary_response(summary: StatisticsSummary) -> DashboardStatisticsSummaryResponse:
    return DashboardStatisticsSummaryResponse(
        win_rate=summary.win_rate,
        expectancy_r=summary.expectancy_r,
        average_r=summary.average_r,
        profit_factor_r=summary.profit_factor_r,
        total_pnl=summary.total_pnl,
        average_confidence_score=summary.average_confidence_score,
        average_quality_score=summary.average_quality_score,
        average_execution_score=summary.average_execution_score,
        average_market_context_score=summary.average_market_context_score,
        average_bias_score=summary.average_bias_score,
    )


def _rolling_response(rolling: RollingStatistics) -> DashboardRollingStatisticsResponse:
    return DashboardRollingStatisticsResponse(
        window=rolling.window,
        rolling=_summary_response(rolling.rolling),
        overall=_summary_response(rolling.overall),
    )


def _mistake_response(result: MistakeRankingResult) -> DashboardMistakeRankingEntryResponse:
    return DashboardMistakeRankingEntryResponse(
        catalog_entry_id=result.catalog_entry_id,
        name=result.name,
        is_active=result.is_active,
        frequency=result.frequency,
        total_cost_r=result.total_cost_r,
        priority=result.priority,
    )


def _trade_response(entry: TradeWithEvaluation) -> DashboardTradeResponse:
    return DashboardTradeResponse(
        id=entry.trade.id,
        market=entry.trade.market,
        direction=entry.trade.direction,
        status=entry.trade.status,
        result=entry.trade.result,
        r_multiple=entry.trade.r_multiple,
        entered_at=entry.trade.entered_at,
    )
