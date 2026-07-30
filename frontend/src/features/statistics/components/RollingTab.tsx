import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable } from "../../../components/DataTable";
import { Select } from "../../../components/Select";
import { getStatisticsRolling } from "../api";
import { OVERALL_COLOR, ROLLING_COLOR } from "../chartColors";
import { formatR, formatRatioAsPercent } from "../format";
import { statisticsKeys } from "../queryKeys";
import { ROLLING_WINDOWS } from "../types";
import type { RollingWindow, StatisticsSummary } from "../types";
import { MetricBarChart } from "./MetricBarChart";

const WINDOW_OPTIONS = ROLLING_WINDOWS.map((window) => ({
  value: String(window),
  label: `Last ${window} Trades`,
}));

interface ComparisonRow {
  series: "Rolling" | "Overall";
  summary: StatisticsSummary;
}

/**
 * Rolling tab — `GET /statistics/rolling?window=` (`TRADEOS_API_SPECIFICATION.md`
 * §6.10). Window selector matching the API's own enum exactly
 * (`TRADEOS_FRONTEND_BLUEPRINT.md` §5.6/§8.6: "10/20/30/50/100/200").
 * Four single-metric Rolling-vs-Overall charts (§12's "Displayed
 * Metrics: Win Rate, Expectancy, Profit Factor, Average R, both
 * windows") plus a 2-row comparison table for the complete field set.
 */
export function RollingTab() {
  const [window, setWindow] = useState<RollingWindow>(10);

  const { data, isLoading } = useQuery({
    queryKey: statisticsKeys.rolling(window),
    queryFn: () => getStatisticsRolling(window),
  });

  const rows: ComparisonRow[] = data
    ? [
        { series: "Rolling", summary: data.rolling },
        { series: "Overall", summary: data.overall },
      ]
    : [];

  const isEmpty =
    data !== undefined &&
    data.overall.win_rate === null &&
    data.overall.profit_factor_r === null &&
    data.overall.total_pnl === 0;

  return (
    <div>
      <div className="max-w-xs">
        <p className="mb-1 text-sm text-text-secondary">Window</p>
        <Select
          value={String(window)}
          onValueChange={(value) => setWindow(Number(value) as RollingWindow)}
          options={WINDOW_OPTIONS}
          aria-label="Window"
        />
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : isEmpty || !data ? (
          <p className="text-sm text-text-secondary">Not enough trade history yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricBarChart
                title="Win Rate"
                data={[
                  { label: "Rolling", value: data.rolling.win_rate, color: ROLLING_COLOR },
                  { label: "Overall", value: data.overall.win_rate, color: OVERALL_COLOR },
                ]}
                formatValue={(v) => formatRatioAsPercent(v)}
                defaultColor={ROLLING_COLOR}
              />
              <MetricBarChart
                title="Expectancy (R)"
                data={[
                  { label: "Rolling", value: data.rolling.expectancy_r, color: ROLLING_COLOR },
                  { label: "Overall", value: data.overall.expectancy_r, color: OVERALL_COLOR },
                ]}
                formatValue={(v) => formatR(v)}
                defaultColor={ROLLING_COLOR}
              />
              <MetricBarChart
                title="Profit Factor"
                data={[
                  { label: "Rolling", value: data.rolling.profit_factor_r, color: ROLLING_COLOR },
                  { label: "Overall", value: data.overall.profit_factor_r, color: OVERALL_COLOR },
                ]}
                formatValue={(v) => formatR(v)}
                defaultColor={ROLLING_COLOR}
              />
              <MetricBarChart
                title="Average R"
                data={[
                  { label: "Rolling", value: data.rolling.average_r, color: ROLLING_COLOR },
                  { label: "Overall", value: data.overall.average_r, color: OVERALL_COLOR },
                ]}
                formatValue={(v) => formatR(v)}
                defaultColor={ROLLING_COLOR}
              />
            </div>

            <div className="mt-6">
              <DataTable<ComparisonRow>
                columns={[
                  { key: "series", header: "", render: (row) => row.series },
                  {
                    key: "win_rate",
                    header: "Win Rate",
                    render: (row) => formatRatioAsPercent(row.summary.win_rate),
                  },
                  {
                    key: "expectancy_r",
                    header: "Expectancy (R)",
                    render: (row) => formatR(row.summary.expectancy_r),
                  },
                  {
                    key: "average_r",
                    header: "Average R",
                    render: (row) => formatR(row.summary.average_r),
                  },
                  {
                    key: "profit_factor_r",
                    header: "Profit Factor",
                    render: (row) => formatR(row.summary.profit_factor_r),
                  },
                ]}
                rows={rows}
                getRowKey={(row) => row.series}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
