"""Statistics presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.10 field-for-field (the response shape
itself is not documented there field-by-field -- inferred from
TRADEOS_FRONTEND_BLUEPRINT.md §8.6's wireframe ("Win Rate, Expectancy,
Profit Factor, Average R, Total P&L, engine averages") and approved
during Sprint 6.1's pre-analysis).
"""

from pydantic import BaseModel


class StatisticsSummaryResponse(BaseModel):
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


class DimensionStatisticsResponse(StatisticsSummaryResponse):
    """`GET /statistics/by-dimension`: "Same metrics, grouped by
    dimension" (§6.10) -- every field `StatisticsSummaryResponse` has,
    plus which group this row is."""

    dimension_value: str
    label: str


class RollingStatisticsResponse(BaseModel):
    """`GET /statistics/rolling`: "Same metrics, computed over the most
    recent N Trades, alongside the all-time comparison" (§6.10). Field
    names `rolling`/`overall` are the literal terminology the frozen
    documents themselves use ("Rolling vs. Overall Comparison",
    `TRADEOS_FRONTEND_BLUEPRINT.md` §12, §8.6), not invented here."""

    window: int
    rolling: StatisticsSummaryResponse
    overall: StatisticsSummaryResponse
