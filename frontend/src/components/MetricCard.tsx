/**
 * Shared MetricCard — TRADEOS_FRONTEND_BLUEPRINT.md §7: "Display one
 * named statistic with its value... Dashboard, Statistics, Playbook
 * performance." First consumer is the Statistics page's Overview tab
 * (Sprint 6.2) — Dashboard (Sprint 8.1) and Playbook (Sprint 7.2) reuse
 * this same component later, unbuilt until this sprint since neither of
 * those pages existed with real data to show yet.
 */
export interface MetricCardProps {
  label: string;
  value: string;
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="mt-1 text-xl font-semibold text-text-primary">{value}</p>
    </div>
  );
}
