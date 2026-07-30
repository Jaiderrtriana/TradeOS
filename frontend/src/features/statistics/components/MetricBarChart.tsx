import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * MetricBarChart — the "Chart" TRADEOS_FRONTEND_BLUEPRINT.md §8/§12
 * names ("Chart — By-Dimension Comparison", "Chart — Rolling vs. Overall
 * Comparison") but never lists among its own §7 reusable components (a
 * documentary omission, noted in Sprint 6.2's pre-analysis, not
 * corrected here). One reusable single-metric bar chart, instantiated
 * once per metric named in §12's "Displayed Metrics" column — avoids
 * ever putting two differently-scaled metrics (a 0-1 ratio, an
 * unbounded R-multiple, a ratio that can exceed 1) on one shared axis,
 * the "never a dual-axis chart" rule applied to bars instead of lines.
 *
 * Each bar's category label (a group name, or "Rolling"/"Overall") is
 * always printed on the x-axis -- identity is carried by that label, not
 * by color alone, so a legend box is never required here even when bars
 * are individually colored (Rolling vs. Overall).
 */
export interface MetricBarChartDatum {
  label: string;
  value: number | null;
  color?: string;
}

export interface MetricBarChartProps {
  title: string;
  data: MetricBarChartDatum[];
  formatValue: (value: number) => string;
  defaultColor: string;
}

export function MetricBarChart({ title, data, formatValue, defaultColor }: MetricBarChartProps) {
  const chartData = data.map((datum) => ({ ...datum, value: datum.value ?? 0 }));

  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <p className="text-sm text-text-secondary">{title}</p>
      <div className="mt-2 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="label"
              stroke="rgb(var(--color-text-muted))"
              tick={{ fill: "rgb(var(--color-text-muted))", fontSize: 12 }}
              axisLine={{ stroke: "rgb(var(--color-border))" }}
              tickLine={false}
            />
            <YAxis
              stroke="rgb(var(--color-text-muted))"
              tick={{ fill: "rgb(var(--color-text-muted))", fontSize: 12 }}
              axisLine={{ stroke: "rgb(var(--color-border))" }}
              tickLine={false}
              width={40}
            />
            <Tooltip
              formatter={(value) => formatValue(Number(value))}
              contentStyle={{
                backgroundColor: "rgb(var(--color-bg-overlay))",
                border: "1px solid rgb(var(--color-border))",
                borderRadius: 4,
                color: "rgb(var(--color-text-primary))",
              }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((datum) => (
                <Cell key={datum.label} fill={datum.color ?? defaultColor} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
