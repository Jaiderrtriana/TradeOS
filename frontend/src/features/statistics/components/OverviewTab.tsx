import { useQuery } from "@tanstack/react-query";

import { MetricCard } from "../../../components/MetricCard";
import { getStatisticsOverview } from "../api";
import { formatPnl, formatR, formatRatioAsPercent, formatScore } from "../format";
import { statisticsKeys } from "../queryKeys";

/**
 * Overview tab — `GET /statistics/overview` (`TRADEOS_API_SPECIFICATION.md`
 * §6.10). "Displayed Information: exactly what each endpoint returns"
 * (`TRADEOS_FRONTEND_BLUEPRINT.md` §5.6) -- every `StatisticsSummary`
 * field gets its own `MetricCard`, nothing invented, nothing omitted.
 */
export function OverviewTab() {
  const { data, isLoading } = useQuery({
    queryKey: statisticsKeys.overview(),
    queryFn: getStatisticsOverview,
  });

  if (isLoading) {
    return <div className="text-sm text-text-secondary">Loading…</div>;
  }

  if (!data) {
    return null;
  }

  const isEmpty =
    data.win_rate === null &&
    data.expectancy_r === null &&
    data.profit_factor_r === null &&
    data.total_pnl === 0;

  if (isEmpty) {
    return <p className="text-sm text-text-secondary">Not enough trade history yet.</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      <MetricCard label="Win Rate" value={formatRatioAsPercent(data.win_rate)} />
      <MetricCard label="Expectancy (R)" value={formatR(data.expectancy_r)} />
      <MetricCard label="Average R" value={formatR(data.average_r)} />
      <MetricCard label="Profit Factor" value={formatR(data.profit_factor_r)} />
      <MetricCard label="Total P&L" value={formatPnl(data.total_pnl)} />
      <MetricCard
        label="Avg. Confidence Score"
        value={formatScore(data.average_confidence_score)}
      />
      <MetricCard label="Avg. Quality Score" value={formatScore(data.average_quality_score)} />
      <MetricCard label="Avg. Execution Score" value={formatScore(data.average_execution_score)} />
      <MetricCard
        label="Avg. Market Context Score"
        value={formatScore(data.average_market_context_score)}
      />
      <MetricCard label="Avg. Bias Score" value={formatScore(data.average_bias_score)} />
    </div>
  );
}
