/**
 * Statistics types — mirrored field-for-field from the real backend
 * schemas (TRADEOS_API_SPECIFICATION.md §6.10; verified directly against
 * backend/app/modules/statistics/presentation/schemas.py, Sprints 6.1-6.2).
 */
export interface StatisticsSummary {
  win_rate: number | null;
  expectancy_r: number | null;
  average_r: number | null;
  profit_factor_r: number | null;
  total_pnl: number;
  average_confidence_score: number | null;
  average_quality_score: number | null;
  average_execution_score: number | null;
  average_market_context_score: number | null;
  average_bias_score: number | null;
}

export interface DimensionStatistics extends StatisticsSummary {
  dimension_value: string;
  label: string;
}

/**
 * `RollingStatistics.window`/`rolling`/`overall` — the literal
 * terminology TRADEOS_FRONTEND_BLUEPRINT.md §12/§8.6 itself uses
 * ("Rolling vs. Overall Comparison"), carried into the backend response
 * shape (Sprint 6.2 pre-analysis) rather than an invented pair of names.
 */
export interface RollingStatistics {
  window: number;
  rolling: StatisticsSummary;
  overall: StatisticsSummary;
}

export type StatisticsDimension = "strategy" | "setup" | "session" | "direction";

/** `TRADEOS_API_SPECIFICATION.md` §6.10: the only valid `?window=` values. */
export const ROLLING_WINDOWS = [10, 20, 30, 50, 100, 200] as const;
export type RollingWindow = (typeof ROLLING_WINDOWS)[number];
