"""
Statistics presentation: `GET /statistics/overview`,
`GET /statistics/by-dimension`, `GET /statistics/rolling` —
`TRADEOS_API_SPECIFICATION.md` §6.10. Read-only; no write endpoint
exists in this module (Domain Invariant DI-11 / ADR-04: Analytics is
never a source of truth, always recomputed fresh from Trading +
Evaluation data).

No pagination envelope on any of the three endpoints — a bare JSON
object (`overview`, `rolling`) or a bare JSON array (`by-dimension`),
same precedent as `GET /mistakes/ranking` (Sprint 5.2): architecturally
identical to a pure, on-demand, never-cached computation (ADR-04/KDD-04),
not a row-scale growing collection.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.list_catalog_entries import (
    build_list_catalog_entries_use_case,
)
from app.modules.statistics.application.get_rolling_statistics import (
    GetRollingStatisticsUseCase,
)
from app.modules.statistics.application.get_statistics_by_dimension import (
    DimensionStatisticsResult,
    GetStatisticsByDimensionUseCase,
)
from app.modules.statistics.application.get_statistics_overview import GetStatisticsOverviewUseCase
from app.modules.statistics.domain.statistics_aggregation import (
    DIMENSIONS,
    ROLLING_WINDOWS,
    RollingStatistics,
    StatisticsSummary,
)
from app.modules.statistics.presentation.schemas import (
    DimensionStatisticsResponse,
    RollingStatisticsResponse,
    StatisticsSummaryResponse,
)
from app.modules.trading.application.list_trade_statistics_facts import (
    build_list_trade_statistics_facts_use_case,
)
from app.platform.db.session import get_db_session
from app.platform.errors import UnprocessableEntityError
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/overview", response_model=StatisticsSummaryResponse)
async def get_statistics_overview(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> StatisticsSummaryResponse:
    use_case = GetStatisticsOverviewUseCase(build_list_trade_statistics_facts_use_case(session))
    summary = await use_case.execute(user_id)
    return _summary_response(summary)


@router.get("/by-dimension", response_model=list[DimensionStatisticsResponse])
async def get_statistics_by_dimension(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    dimension: str = Query(...),
) -> list[DimensionStatisticsResponse]:
    if dimension not in DIMENSIONS:
        # `strategy`/`setup`/`session`/`direction` are the only
        # dimensions any document names for this endpoint -- no other
        # value is invented as groupable.
        raise UnprocessableEntityError(f"Unsupported dimension: '{dimension}'.")

    use_case = GetStatisticsByDimensionUseCase(
        build_list_trade_statistics_facts_use_case(session),
        build_list_catalog_entries_use_case(session),
    )
    results = await use_case.execute(user_id, dimension)
    return [_dimension_response(result) for result in results]


@router.get("/rolling", response_model=RollingStatisticsResponse)
async def get_statistics_rolling(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    window: int = Query(...),
) -> RollingStatisticsResponse:
    if window not in ROLLING_WINDOWS:
        # 10/20/30/50/100/200 are the only windows any document names for
        # this endpoint -- no other value is invented as valid
        # (`TRADEOS_API_SPECIFICATION.md` §6.10), same "validate at the
        # router, never pass an invalid value down" discipline as
        # `dimension` above.
        raise UnprocessableEntityError(f"Unsupported window: '{window}'.")

    use_case = GetRollingStatisticsUseCase(build_list_trade_statistics_facts_use_case(session))
    rolling = await use_case.execute(user_id, window)
    return _rolling_response(rolling)


def _summary_response(summary: StatisticsSummary) -> StatisticsSummaryResponse:
    return StatisticsSummaryResponse(
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


def _dimension_response(result: DimensionStatisticsResult) -> DimensionStatisticsResponse:
    return DimensionStatisticsResponse(
        dimension_value=result.dimension_value,
        label=result.label,
        **_summary_response(result.summary).model_dump(),
    )


def _rolling_response(rolling: RollingStatistics) -> RollingStatisticsResponse:
    return RollingStatisticsResponse(
        window=rolling.window,
        rolling=_summary_response(rolling.rolling),
        overall=_summary_response(rolling.overall),
    )
