import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable } from "../../../components/DataTable";
import { Select } from "../../../components/Select";
import { getStatisticsByDimension } from "../api";
import { formatPnl, formatR, formatRatioAsPercent } from "../format";
import { statisticsKeys } from "../queryKeys";
import type { DimensionStatistics, StatisticsDimension } from "../types";
import { ROLLING_COLOR } from "../chartColors";
import { MetricBarChart } from "./MetricBarChart";

const DIMENSION_OPTIONS: { value: StatisticsDimension; label: string }[] = [
  { value: "strategy", label: "Strategy" },
  { value: "setup", label: "Setup" },
  { value: "session", label: "Session" },
  { value: "direction", label: "Direction" },
];

/**
 * By Dimension tab — `GET /statistics/by-dimension?dimension=`
 * (`TRADEOS_API_SPECIFICATION.md` §6.10). Three single-metric charts
 * (`TRADEOS_FRONTEND_BLUEPRINT.md` §12's "Displayed Metrics: Win Rate,
 * Expectancy, Profit Factor per group") plus the full data in tabular
 * form (§8.6 wireframe: "Chart... DataTable (same data, tabular form)").
 * Row-click drill-down into a filtered Trades List / Playbook Setup
 * (§12, §18) is explicitly out of this sprint's approved scope.
 */
export function ByDimensionTab() {
  const [dimension, setDimension] = useState<StatisticsDimension>("strategy");

  const { data, isLoading } = useQuery({
    queryKey: statisticsKeys.byDimension(dimension),
    queryFn: () => getStatisticsByDimension(dimension),
  });

  const groups = data ?? [];

  return (
    <div>
      <div className="max-w-xs">
        <p className="mb-1 text-sm text-text-secondary">Dimension</p>
        <Select
          value={dimension}
          onValueChange={(value) => setDimension(value as StatisticsDimension)}
          options={DIMENSION_OPTIONS}
          aria-label="Dimension"
        />
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : groups.length === 0 ? (
          <p className="text-sm text-text-secondary">Not enough trade history yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <MetricBarChart
                title="Win Rate"
                data={groups.map((g) => ({ label: g.label, value: g.win_rate }))}
                formatValue={(v) => formatRatioAsPercent(v)}
                defaultColor={ROLLING_COLOR}
              />
              <MetricBarChart
                title="Expectancy (R)"
                data={groups.map((g) => ({ label: g.label, value: g.expectancy_r }))}
                formatValue={(v) => formatR(v)}
                defaultColor={ROLLING_COLOR}
              />
              <MetricBarChart
                title="Profit Factor"
                data={groups.map((g) => ({ label: g.label, value: g.profit_factor_r }))}
                formatValue={(v) => formatR(v)}
                defaultColor={ROLLING_COLOR}
              />
            </div>

            <div className="mt-6">
              <DataTable<DimensionStatistics>
                columns={[
                  { key: "label", header: "Group", render: (row) => row.label },
                  {
                    key: "win_rate",
                    header: "Win Rate",
                    render: (row) => formatRatioAsPercent(row.win_rate),
                  },
                  {
                    key: "expectancy_r",
                    header: "Expectancy (R)",
                    render: (row) => formatR(row.expectancy_r),
                  },
                  {
                    key: "average_r",
                    header: "Average R",
                    render: (row) => formatR(row.average_r),
                  },
                  {
                    key: "profit_factor_r",
                    header: "Profit Factor",
                    render: (row) => formatR(row.profit_factor_r),
                  },
                  {
                    key: "total_pnl",
                    header: "Total P&L",
                    render: (row) => formatPnl(row.total_pnl),
                  },
                ]}
                rows={groups}
                getRowKey={(row) => row.dimension_value}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
