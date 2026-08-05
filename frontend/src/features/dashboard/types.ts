/**
 * Dashboard types — mirrored field-for-field from the real backend
 * schema (`TRADEOS_API_SPECIFICATION.md` §6.12; verified directly
 * against `backend/app/modules/dashboard/presentation/schemas.py`,
 * Sprint 8.1).
 *
 * These deliberately duplicate field sets already defined in
 * `features/statistics/types.ts`/`features/mistakes/types.ts` rather
 * than importing them — same "each feature owns its own types"
 * discipline `features/playbook/types.ts` already establishes
 * (`PlaybookSetupPerformance` duplicates `StatisticsSummary`'s fields,
 * Sprint 7.2), and the one this project's own `eslint-plugin-boundaries`
 * config enforces at build time: a feature's `types.ts` may only import
 * its own feature or `shared`/`component`/`api`/`auth`/`layout` — never
 * another feature's internals (`eslint.config.js`, Architecture
 * Readiness Review).
 */
export interface DashboardStatisticsSummary {
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

export interface DashboardRollingStatistics {
  window: number;
  rolling: DashboardStatisticsSummary;
  overall: DashboardStatisticsSummary;
}

export interface DashboardMistakeRankingEntry {
  catalog_entry_id: string;
  name: string;
  is_active: boolean;
  frequency: number;
  total_cost_r: number | null;
  priority: number;
}

export interface DashboardTrade {
  id: string;
  market: string;
  direction: "long" | "short";
  status: "planned" | "open" | "closed";
  result: "tp" | "sl" | "be" | null;
  r_multiple: number | null;
  entered_at: string | null;
}

export interface DashboardSummary {
  overview: DashboardStatisticsSummary;
  rolling: DashboardRollingStatistics;
  top_mistakes: DashboardMistakeRankingEntry[];
  recent_trades: DashboardTrade[];
}
