import { MetricCard } from "../../../components/MetricCard";
import type { PlaybookSetupPerformance } from "../types";

function formatRatioAsPercent(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatR(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

function formatPnl(value: number): string {
  return value.toFixed(2);
}

function formatScore(value: number | null): string {
  return value === null ? "—" : value.toFixed(1);
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's Playbook Setup Detail row:
 * "Performance numbers are never edited here — read-only, sourced
 * live." This card only ever renders the `performance` object the
 * backend already composed from Statistics (`GetPlaybookSetupUseCase`,
 * Sprint 7.1) — no computation, no formula, no client-side fallback
 * value happens here.
 */
export function PerformanceCard({ performance }: { performance: PlaybookSetupPerformance }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-text-primary">Performance</h2>
      <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard label="Win Rate" value={formatRatioAsPercent(performance.win_rate)} />
        <MetricCard label="Expectancy (R)" value={formatR(performance.expectancy_r)} />
        <MetricCard label="Average R" value={formatR(performance.average_r)} />
        <MetricCard label="Profit Factor" value={formatR(performance.profit_factor_r)} />
        <MetricCard label="Total P&L" value={formatPnl(performance.total_pnl)} />
        <MetricCard
          label="Avg. Confidence Score"
          value={formatScore(performance.average_confidence_score)}
        />
        <MetricCard
          label="Avg. Quality Score"
          value={formatScore(performance.average_quality_score)}
        />
        <MetricCard
          label="Avg. Execution Score"
          value={formatScore(performance.average_execution_score)}
        />
        <MetricCard
          label="Avg. Market Context Score"
          value={formatScore(performance.average_market_context_score)}
        />
        <MetricCard label="Avg. Bias Score" value={formatScore(performance.average_bias_score)} />
      </div>
    </div>
  );
}
